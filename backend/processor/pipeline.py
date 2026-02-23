"""
LLM Pipeline - Main orchestrator for the 3-layer analysis pipeline.

Pipeline Flow (fully autonomous, called by scheduler):
1. Crawl data from sources (SBV, etc.)
2. Transform raw data → CrawlerOutput (metrics, events, calendar)
3. Save metrics → indicators + indicator_history
4. Save calendar → calendar_events
5. Process events through 3 LLM layers:
   - Layer 1: Classification (filter relevant, check dedup)
   - Layer 2: Scoring (with context)
   - Layer 3: Ranking (decay, boost, sections)
6. Save events to database
7. Create signals and link themes
8. Check watchlist triggers
9. Save run history
"""
import hashlib
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from loguru import logger

from config import settings
from database.session import get_session, init_engine
from repositories import (
    EventRepository,
    IndicatorRepository,
    SignalRepository,
    ThemeRepository,
    WatchlistRepository,
    RunHistoryRepository,
)
from data_transformers import CrawlerOutput
from data_transformers.models import MetricRecord, EventRecord, CalendarRecord

from llm import set_llm_context
from .classifier import Classifier
from .scorer import Scorer
from .ranker import Ranker
from .context_builder import ContextBuilder
from .narrative_synthesizer import NarrativeSynthesizer


class Pipeline:
    """
    Main pipeline orchestrator.
    
    Fully autonomous: crawls, transforms, processes, and saves data.
    Called by scheduler on hourly interval.
    """
    
    def __init__(
        self, 
        data_dir: Path = None,
        lookback_days: int = 7
    ):
        self.data_dir = data_dir or settings.DATA_DIR
        self.lookback_days = lookback_days
        
        # LLM components (sync, wrapped when called)
        self.classifier = Classifier()
        self.scorer = Scorer()
        self.ranker = Ranker()
        self.narrative_synthesizer = NarrativeSynthesizer()
        
    async def run(self) -> dict:
        """
        Run the complete pipeline.
        
        Returns:
            Dict with run results and statistics
        """
        run_start = datetime.now()
        run_id = run_start.strftime("%Y%m%d_%H%M%S")
        run_date = date.today()
        
        # Set LLM context for call logging
        set_llm_context(run_id=run_id)
        
        logger.info(f"=== Starting Pipeline Run {run_id} ===")
        
        results = {
            "run_id": run_id,
            "run_date": str(run_date),
            "status": "in_progress",
            "steps": {},
            "stats": {}
        }
        
        try:
            # Initialize database engine
            await init_engine()
            
            # ============================================
            # Step 0: Get existing titles for deduplication
            # ============================================
            logger.info("Step 0: Fetching existing titles for deduplication...")
            
            existing_titles_by_source = {}
            async with get_session() as session:
                events_repo = EventRepository(session)
                # Get titles for each source we'll crawl
                for source in ["sbv", "vneconomy", "cafef", "vnexpress"]:
                    titles = await events_repo.get_recent_titles(source=source, days=self.lookback_days)
                    existing_titles_by_source[source] = titles
                    logger.debug(f"Found {len(titles)} existing titles for {source}")
            
            total_existing = sum(len(t) for t in existing_titles_by_source.values())
            logger.info(f"Found {total_existing} existing titles across all sources")
            
            # ============================================
            # Step 1: Crawl data from sources
            # ============================================
            logger.info("Step 1: Crawling data from sources...")
            
            crawler_outputs = await self._crawl_all_sources(existing_titles_by_source)
            
            results["steps"]["crawl"] = {
                "sources": [o.source for o in crawler_outputs],
                "total_metrics": sum(o.metrics_count for o in crawler_outputs),
                "total_events": sum(o.events_count for o in crawler_outputs),
                "total_calendar": sum(o.calendar_count for o in crawler_outputs),
            }
            logger.info(f"Crawled {len(crawler_outputs)} sources")
            
            # ============================================
            # Step 2-8: Process in database session
            # ============================================
            async with get_session() as session:
                # Initialize repositories
                events_repo = EventRepository(session)
                indicators_repo = IndicatorRepository(session)
                signals_repo = SignalRepository(session)
                themes_repo = ThemeRepository(session)
                watchlist_repo = WatchlistRepository(session)
                run_history_repo = RunHistoryRepository(session)
                
                # ============================================
                # Step 2: Save metrics to indicators
                # ============================================
                logger.info("Step 2: Saving metrics to database...")
                
                metrics_saved = 0
                history_saved = 0
                
                for output in crawler_outputs:
                    for metric in output.metrics:
                        try:
                            # Upsert indicator
                            indicator = await self._save_metric(indicators_repo, metric)
                            if indicator:
                                metrics_saved += 1
                                
                                # Add to history
                                history = await indicators_repo.add_history(
                                    indicator_id=metric.metric_id,
                                    value=metric.value,
                                    record_date=metric.date,
                                    source=metric.source,
                                    volume=metric.attributes.get('volume'),
                                )
                                if history:
                                    history_saved += 1
                        except Exception as e:
                            logger.warning(f"Failed to save metric {metric.metric_id}: {e}")
                
                results["steps"]["metrics"] = {
                    "indicators_updated": metrics_saved,
                    "history_records": history_saved,
                }
                logger.info(f"Saved {metrics_saved} indicators, {history_saved} history records")
                
                # ============================================
                # Step 3: Save calendar events
                # ============================================
                logger.info("Step 3: Saving calendar events...")
                
                calendar_saved = 0
                for output in crawler_outputs:
                    for cal in output.calendar:
                        try:
                            await run_history_repo.add_calendar_event(
                                event_name=cal.event_name,
                                event_date=cal.date,
                                event_time=cal.time,
                                country=cal.country,
                                importance=cal.importance,
                                forecast=cal.forecast,
                                previous=cal.previous,
                            )
                            calendar_saved += 1
                        except Exception as e:
                            # Likely duplicate, skip
                            logger.debug(f"Calendar event skipped (duplicate?): {e}")
                
                results["steps"]["calendar"] = {"saved": calendar_saved}
                logger.info(f"Saved {calendar_saved} calendar events")
                
                # ============================================
                # Step 4: Collect all events for LLM processing
                # ============================================
                all_events = []
                for output in crawler_outputs:
                    for event in output.events:
                        all_events.append(event)
                
                logger.info(f"Step 4: Processing {len(all_events)} events through LLM pipeline...")
                
                # ============================================
                # Step 5: Layer 1 - Classification
                # ============================================
                # Note: Deduplication is now done at crawler level by title matching.
                # We still compute hash for storage but skip DB lookup here.
                logger.info("Step 5: Layer 1 - Classification...")
                set_llm_context(task_type="classification")
                
                classified_events = []
                irrelevant_skipped = 0
                
                for event in all_events:
                    # Compute hash for storage (not for dedup - that's done in crawler)
                    hash_value = self._compute_hash(event)
                    
                    # Classify
                    news_dict = self._event_to_dict(event)
                    classification = self.classifier.classify(news_dict)
                    
                    if not classification.is_market_relevant:
                        irrelevant_skipped += 1
                        logger.debug(f"Skipping irrelevant: {event.title[:50]}...")
                        continue
                    
                    # Merge classification into event data
                    classified_events.append({
                        "event": event,
                        "hash": hash_value,
                        "classification": classification,
                    })
                
                results["steps"]["classify"] = {
                    "total": len(all_events),
                    "relevant": len(classified_events),
                    "irrelevant_skipped": irrelevant_skipped,
                }
                logger.info(f"Classification: {len(classified_events)}/{len(all_events)} relevant ({irrelevant_skipped} irrelevant)")
                
                # ============================================
                # Step 6: Build context for scoring
                # ============================================
                logger.info("Step 6: Building context...")
                
                # Get active signals
                active_signals = await signals_repo.get_active()
                active_signals_list = [
                    {
                        "id": sig.id,
                        "prediction": sig.prediction,
                        "target_indicator": sig.target_indicator,
                        "direction": sig.direction,
                        "confidence": sig.confidence,
                        "expires_at": sig.expires_at.isoformat() if sig.expires_at else None,
                    }
                    for sig in active_signals
                ]
                
                # Get active themes
                active_themes = await themes_repo.get_active_and_emerging()
                active_themes_list = [
                    {
                        "id": theme.id,
                        "name": theme.name,
                        "strength": theme.strength,
                        "event_count": theme.event_count,
                        "status": theme.status,
                    }
                    for theme in active_themes
                ]
                
                # Get indicator trends
                all_indicator_ids = []
                for ce in classified_events:
                    linked = ce["classification"].linked_indicators or []
                    all_indicator_ids.extend(linked)
                all_indicator_ids = list(set(all_indicator_ids))
                
                indicator_trends = await indicators_repo.get_trends(
                    all_indicator_ids, 
                    days=self.lookback_days
                )
                
                # Build context summary (simplified)
                context_summary = self._build_context_summary(
                    active_signals_list,
                    active_themes_list,
                    indicator_trends,
                    self.lookback_days
                )
                
                results["steps"]["context"] = {
                    "active_signals": len(active_signals_list),
                    "active_themes": len(active_themes_list),
                    "indicators_tracked": len(all_indicator_ids),
                }
                
                # ============================================
                # Step 7: Layer 2 - Scoring
                # ============================================
                logger.info(f"Step 7: Layer 2 - Scoring {len(classified_events)} events...")
                set_llm_context(task_type="scoring")
                
                scored_events = []
                for ce in classified_events:
                    event = ce["event"]
                    classification = ce["classification"]
                    
                    # Prepare item for scoring
                    news_dict = self._event_to_dict(event)
                    news_dict["category"] = classification.category
                    news_dict["linked_indicators"] = classification.linked_indicators
                    
                    # Score
                    try:
                        scoring = self.scorer.score(
                            news_dict,
                            previous_context_summary=context_summary,
                            active_signals=active_signals_list,
                            active_themes=active_themes_list,
                            lookback_days=self.lookback_days,
                        )
                        
                        scored_events.append({
                            **ce,
                            "scoring": scoring,
                        })
                    except Exception as e:
                        logger.error(f"Scoring failed for {event.title[:50]}: {e}")
                        # Use default score
                        scored_events.append({
                            **ce,
                            "scoring": None,
                        })
                
                results["steps"]["score"] = {
                    "scored": len(scored_events),
                }
                logger.info(f"Scored {len(scored_events)} events")
                
                # ============================================
                # Step 8: Save events to database
                # ============================================
                logger.info("Step 8: Saving events...")
                
                events_saved = 0
                signals_created = 0
                themes_updated = 0
                
                for se in scored_events:
                    event = se["event"]
                    classification = se["classification"]
                    scoring = se["scoring"]
                    hash_value = se["hash"]
                    
                    # Get base score
                    base_score = 50  # default
                    score_factors = None
                    causal_analysis = None
                    
                    if scoring:
                        base_score = scoring.base_score or 50
                        score_factors = scoring.score_factors
                        causal_analysis = scoring.causal_analysis
                    
                    try:
                        # Create event (returns None if duplicate hash exists)
                        new_event = await events_repo.create_event(
                            title=event.title,
                            content=event.content,
                            summary=event.summary,
                            source=event.source,
                            source_url=event.source_url,
                            category=classification.category,
                            region="vietnam",
                            is_market_relevant=True,
                            linked_indicators=classification.linked_indicators or [],
                            published_at=event.published_at,
                            hash_value=hash_value,
                        )
                        
                        # Skip if duplicate event (already exists)
                        if new_event is None:
                            logger.debug(f"Skipping duplicate event: {event.title[:50]}...")
                            continue
                        
                        # Update scores
                        await events_repo.update_scores(
                            event_id=new_event.id,
                            base_score=base_score,
                            score_factors=score_factors,
                            current_score=float(base_score),
                        )
                        events_saved += 1
                        
                        # Save causal analysis
                        if causal_analysis and causal_analysis.get("chain"):
                            await events_repo.add_causal_analysis(
                                event_id=new_event.id,
                                template_id=causal_analysis.get("matched_template_id"),
                                chain_steps=causal_analysis.get("chain", []),
                                confidence=causal_analysis.get("confidence"),
                                affected_indicators=classification.linked_indicators or [],
                                reasoning=causal_analysis.get("reasoning"),
                            )
                        
                        # Handle signal output from scoring
                        if scoring and scoring.signal_output:
                            sig_out = scoring.signal_output
                            # Check if signal should be created (SignalOutput is a dataclass)
                            if sig_out.create_signal and sig_out.prediction:
                                expires_at = None
                                if sig_out.timeframe_days:
                                    expires_at = datetime.now() + timedelta(days=sig_out.timeframe_days)
                                
                                await signals_repo.create_signal(
                                    prediction=sig_out.prediction,
                                    source_event_id=new_event.id,
                                    target_indicator=sig_out.target_indicator,
                                    target_range_low=sig_out.target_range_low,
                                    target_range_high=sig_out.target_range_high,
                                    direction=sig_out.direction,
                                    confidence=sig_out.confidence or "medium",
                                    timeframe_days=sig_out.timeframe_days,
                                    expires_at=expires_at,
                                    reasoning=sig_out.reasoning,
                                    related_indicators=classification.linked_indicators or [],
                                )
                                signals_created += 1
                        
                        # Handle theme link from scoring
                        if scoring and scoring.theme_link:
                            theme_link = scoring.theme_link
                            # ThemeLink is a dataclass - check for existing_theme_id or new_theme
                            
                            # Link to existing theme by ID
                            if theme_link.existing_theme_id:
                                existing_theme = await themes_repo.get(theme_link.existing_theme_id)
                                if existing_theme:
                                    await themes_repo.add_event(existing_theme.id, new_event.id)
                                    themes_updated += 1
                            
                            # Create new theme
                            elif theme_link.create_new_theme and theme_link.new_theme:
                                new_theme_data = theme_link.new_theme
                                theme_name = new_theme_data.get("name")
                                if theme_name:
                                    # Check if theme already exists by name
                                    existing_theme = await themes_repo.get_by_name(theme_name)
                                    if existing_theme:
                                        await themes_repo.add_event(existing_theme.id, new_event.id)
                                    else:
                                        await themes_repo.create_theme(
                                            name=theme_name,
                                            name_vi=new_theme_data.get("name_vi"),
                                            description=new_theme_data.get("description"),
                                            event_id=new_event.id,
                                            related_indicators=classification.linked_indicators or [],
                                        )
                                    themes_updated += 1
                        
                    except Exception as e:
                        # Rollback to clean session state before continuing
                        await session.rollback()
                        logger.error(f"Failed to save event {event.title[:50]}: {e}")
                
                results["steps"]["save"] = {
                    "events_saved": events_saved,
                    "signals_created": signals_created,
                    "themes_updated": themes_updated,
                }
                logger.info(f"Saved {events_saved} events, {signals_created} signals, {themes_updated} themes")
                
                # ============================================
                # Step 8.5: Update Trend Stats & Narratives
                # Only recompute themes affected by this run
                # (themes that had events/signals added)
                # ============================================
                logger.info("Step 8.5: Updating trend stats and generating narratives...")
                
                narratives_updated = 0
                affected_theme_ids = set()
                
                # Collect theme IDs affected by this pipeline run
                # These are themes that had events or signals added in Step 8
                if themes_updated > 0 or signals_created > 0:
                    # Query themes that were updated in this run window
                    all_themes = await themes_repo.get_active_and_emerging()
                    for theme in all_themes:
                        # Check if theme was touched: updated_at within last few minutes
                        if theme.updated_at and (datetime.now() - theme.updated_at).total_seconds() < 300:
                            affected_theme_ids.add(theme.id)
                
                if affected_theme_ids:
                    logger.info(f"Recomputing stats for {len(affected_theme_ids)} affected themes")
                    
                    for theme_id in affected_theme_ids:
                        try:
                            theme = await themes_repo.get(theme_id)
                            if not theme:
                                continue
                            
                            # Recompute trend stats (urgency, signals_count, etc)
                            await themes_repo.recompute_trend_stats(theme.id)
                            
                            # Get signals for this theme
                            theme_signals = await signals_repo.get_by_theme(theme.id, limit=20)
                            active_signals = [s for s in theme_signals if s.status == 'active']
                            
                            if active_signals:
                                # Prepare signal data for synthesizer
                                # Include full detail for better narrative generation
                                signals_data = [
                                    {
                                        'prediction': s.prediction,
                                        'direction': s.direction,
                                        'target_indicator': s.target_indicator,
                                        'target_range_low': s.target_range_low,
                                        'target_range_high': s.target_range_high,
                                        'confidence': s.confidence,
                                        'expires_at': str(s.expires_at) if s.expires_at else None,
                                        'reasoning': s.reasoning,
                                    }
                                    for s in active_signals
                                ]
                                
                                # Get related indicators
                                indicators_data = []
                                if theme.related_indicators:
                                    for ind_id in theme.related_indicators[:5]:
                                        indicator = await indicators_repo.get(ind_id)
                                        if indicator:
                                            indicators_data.append({
                                                'indicator_id': ind_id,
                                                'name': indicator.name,
                                                'current_value': indicator.current_value,
                                                'unit': indicator.unit,
                                            })
                                
                                # Generate narrative via LLM (sync call wrapped in thread)
                                # NarrativeSynthesizer.synthesize() is sync because
                                # LLMClient.generate() uses blocking HTTP. We run it
                                # in a thread to avoid blocking the async event loop.
                                import asyncio
                                narrative = await asyncio.to_thread(
                                    self.narrative_synthesizer.synthesize,
                                    theme_name=theme.name,
                                    theme_description=theme.description or '',
                                    first_seen=str(theme.first_seen) if theme.first_seen else '',
                                    strength=theme.strength or 0,
                                    signals=signals_data,
                                    indicators=indicators_data,
                                )
                                
                                if narrative:
                                    await themes_repo.update_narrative(theme.id, narrative)
                                    narratives_updated += 1
                        except Exception as e:
                            logger.warning(f"Failed to update narrative for theme {theme_id}: {e}")
                
                results["steps"]["narratives"] = {
                    "affected_themes": len(affected_theme_ids),
                    "narratives_updated": narratives_updated,
                }
                logger.info(f"Updated {narratives_updated} trend narratives ({len(affected_theme_ids)} affected)")
                
                # ============================================
                # Step 9: Layer 3 - Rank all active events
                # ============================================
                logger.info("Step 9: Layer 3 - Ranking all active events...")
                set_llm_context(task_type="ranking")
                
                # Get all active events
                all_active = await events_repo.get_active_events(max_age_days=30)
                all_active_dicts = [self._db_event_to_dict(e) for e in all_active]
                
                # Detect hot topics
                hot_topics = self.ranker.detect_hot_topics(all_active_dicts)
                hot_topic_names = [t["topic"] for t in hot_topics]
                
                # Get active theme names for boost
                active_theme_names = [t.name for t in active_themes]
                
                # Rank events
                ranking_result = self.ranker.rank_all_events(
                    all_active_dicts,
                    active_themes=active_theme_names,
                    hot_topics=hot_topic_names,
                )
                
                # Update events in database
                key_events_count = 0
                other_news_count = 0
                archived_count = 0
                
                for r in ranking_result.get("rankings", []):
                    await events_repo.update_scores(
                        event_id=r["event_id"],
                        base_score=r.get("original_score", 50),
                        current_score=r["final_score"],
                        decay_factor=r["decay_factor"],
                        boost_factor=r["boost_factor"],
                        display_section=r["display_section"],
                    )
                    
                    if r["display_section"] == "key_events":
                        key_events_count += 1
                    elif r["display_section"] == "other_news":
                        other_news_count += 1
                    else:
                        archived_count += 1
                
                results["steps"]["rank"] = {
                    "ranked": len(ranking_result.get("rankings", [])),
                    "key_events": key_events_count,
                    "other_news": other_news_count,
                    "archived": archived_count,
                    "hot_topics": len(hot_topics),
                }
                logger.info(f"Ranked {len(ranking_result.get('rankings', []))} events: {key_events_count} key, {other_news_count} other")
                
                # ============================================
                # Step 10: Check watchlist triggers
                # ============================================
                logger.info("Step 10: Checking watchlist triggers...")
                
                watchlist_triggered = 0
                active_watchlist = await watchlist_repo.get_active()
                
                for item in active_watchlist:
                    triggered = False
                    trigger_event_id = None
                    
                    if item.trigger_type == "keyword":
                        # Check if keywords appear in today's events
                        keywords = item.trigger_keywords or []
                        if keywords:
                            for se in scored_events:
                                event = se["event"]
                                title_lower = (event.title or "").lower()
                                content_lower = (event.content or "").lower()
                                for keyword in keywords:
                                    if keyword.lower() in title_lower or keyword.lower() in content_lower:
                                        triggered = True
                                        trigger_event_id = event.id if hasattr(event, 'id') else None
                                        break
                                if triggered:
                                    break
                    
                    elif item.trigger_type == "indicator":
                        # Check indicator threshold
                        triggered = await watchlist_repo.check_indicator_trigger(
                            item.id, 
                            indicators_repo
                        )
                    
                    elif item.trigger_type == "date":
                        # Check if trigger date reached
                        if item.trigger_date:
                            if date.today() >= item.trigger_date:
                                triggered = True
                    
                    if triggered:
                        await watchlist_repo.trigger(item.id, trigger_event_id)
                        watchlist_triggered += 1
                
                results["steps"]["watchlist"] = {
                    "checked": len(active_watchlist),
                    "triggered": watchlist_triggered,
                }
                
                # ============================================
                # Step 11: Save run history
                # ============================================
                logger.info("Step 11: Saving run history...")
                
                summary = self._generate_run_summary(results)
                
                await run_history_repo.create_run(
                    news_count=len(all_events),
                    events_extracted=events_saved,
                    events_key=key_events_count,
                    events_other=other_news_count,
                    signals_created=signals_created,
                    themes_updated=themes_updated,
                    watchlist_triggered=watchlist_triggered,
                    summary=summary,
                    status="success",
                )
                
                # Session auto-commits here
            
            # ============================================
            # Done!
            # ============================================
            results["status"] = "success"
            results["stats"] = {
                "events_created": events_saved,
                "classified_items": len(classified_events),
            }
            results["duration_seconds"] = (datetime.now() - run_start).total_seconds()
            
            logger.info(f"=== Pipeline Run Complete in {results['duration_seconds']:.1f}s ===")
            logger.info(summary)
            
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            
            # Try to save failed run
            try:
                async with get_session() as session:
                    run_history_repo = RunHistoryRepository(session)
                    await run_history_repo.create_run(
                        news_count=0,
                        events_extracted=0,
                        events_key=0,
                        events_other=0,
                        summary=f"Pipeline failed: {str(e)}",
                        status="failed",
                    )
            except:
                pass
        
        return results
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    async def _crawl_all_sources(
        self, 
        existing_titles_by_source: dict[str, set] = None
    ) -> List[CrawlerOutput]:
        """
        Crawl all configured sources and return transformed outputs.
        
        Args:
            existing_titles_by_source: Dict mapping source name to set of existing titles
                                       for deduplication at crawler level.
        """
        from crawlers import SBVCrawler
        
        existing_titles_by_source = existing_titles_by_source or {}
        outputs = []
        
        # SBV Crawler
        try:
            logger.info("Crawling SBV...")
            crawler = SBVCrawler(data_dir=self.data_dir)
            
            # Use run() instead of fetch() to get full article content + PDF extraction
            # max_articles=None means fetch ALL articles (default behavior)
            # For faster runs during development, you can set max_articles=5
            raw_result = await crawler.run(
                max_articles=None,  # Fetch all articles with full content
                extract_pdf=True,   # Extract text from PDF attachments
                save_raw=False,     # Save raw output to data/raw for debugging
                existing_titles=existing_titles_by_source.get("sbv", set()),
            )
            
            if raw_result.success:
                # Transform using crawler's transformer
                output = crawler.transformer.transform(raw_result.to_dict())
                outputs.append(output)
                logger.info(f"SBV: {output.summary()}")
            else:
                logger.warning(f"SBV crawl failed: {raw_result.error}")
                
        except Exception as e:
            logger.error(f"SBV crawler error: {e}")
        
        # VnEconomy Crawler
        try:
            logger.info("Crawling VnEconomy...")
            from crawlers.vneconomy_crawler import VnEconomyCrawler
            
            vneconomy_crawler = VnEconomyCrawler(data_dir=self.data_dir)
            
            # Use run() to get full article content
            # max_articles=20 to limit during initial testing, set to None for full crawl
            raw_result = await vneconomy_crawler.run(
                max_articles=20,  # Limit to 20 articles for faster runs
                save_raw=False,   # Set True to save raw data for debugging
                existing_titles=existing_titles_by_source.get("vneconomy", set()),
            )
            
            if raw_result.success:
                # Transform using crawler's transformer
                output = vneconomy_crawler.transformer.transform(raw_result.to_dict())
                outputs.append(output)
                logger.info(f"VnEconomy: {output.summary()}")
            else:
                logger.warning(f"VnEconomy crawl failed: {raw_result.error}")
                
        except Exception as e:
            logger.error(f"VnEconomy crawler error: {e}")
        
        # CafeF Crawler
        try:
            logger.info("Crawling CafeF...")
            from crawlers.cafef_crawler import CafeFCrawler
            
            cafef_crawler = CafeFCrawler(data_dir=self.data_dir)
            
            raw_result = await cafef_crawler.run(
                max_articles=20,  # Limit for faster runs
                save_raw=False,
                existing_titles=existing_titles_by_source.get("cafef", set()),
            )
            
            if raw_result.success:
                output = cafef_crawler.transformer.transform(raw_result.to_dict())
                outputs.append(output)
                logger.info(f"CafeF: {output.summary()}")
            else:
                logger.warning(f"CafeF crawl failed: {raw_result.error}")
                
        except Exception as e:
            logger.error(f"CafeF crawler error: {e}")
        
        # VnExpress Crawler
        try:
            logger.info("Crawling VnExpress...")
            from crawlers.vnexpress_crawler import VnExpressCrawler
            
            vnexpress_crawler = VnExpressCrawler(data_dir=self.data_dir)
            
            raw_result = await vnexpress_crawler.run(
                max_articles=20,  # Limit for faster runs
                save_raw=False,
                existing_titles=existing_titles_by_source.get("vnexpress", set()),
            )
            
            if raw_result.success:
                output = vnexpress_crawler.transformer.transform(raw_result.to_dict())
                outputs.append(output)
                logger.info(f"VnExpress: {output.summary()}")
            else:
                logger.warning(f"VnExpress crawl failed: {raw_result.error}")
                
        except Exception as e:
            logger.error(f"VnExpress crawler error: {e}")
        
        # Vietcombank Exchange Rates Crawler
        try:
            logger.info("Crawling Vietcombank exchange rates...")
            from crawlers.vietcombank_crawler import VietcombankCrawler
            
            vcb_crawler = VietcombankCrawler(data_dir=self.data_dir)
            
            raw_result = await vcb_crawler.run(
                save_raw=False,
            )
            
            if raw_result.success:
                output = vcb_crawler.transformer.transform(raw_result.to_dict())
                outputs.append(output)
                logger.info(f"Vietcombank: {output.summary()}")
                # DEBUG: log each metric so we can verify in scheduler logs
                for m in output.metrics:
                    logger.debug(
                        f"[Vietcombank] metric_id={m.metric_id} "
                        f"value={m.value} unit={m.unit} date={m.date} "
                        f"source={m.source}"
                    )
            else:
                logger.warning(
                    f"Vietcombank crawl failed: {raw_result.error} "
                    f"(data items returned: {len(raw_result.data)})"
                )
                
        except Exception as e:
            logger.exception(f"Vietcombank crawler error: {e}")  # full traceback in logs
        
        # TODO: Add more crawlers here (Global, Calendar)
        
        return outputs
    
    async def _save_metric(
        self, 
        repo: IndicatorRepository, 
        metric: MetricRecord
    ):
        """Save a metric to the indicators table."""
        # Determine category from metric type
        category = self._get_indicator_category(metric.metric_type)
        
        # Calculate trend if we have previous value
        trend = None
        change = None
        change_pct = None
        
        latest = await repo.get_latest_history(metric.metric_id)
        if latest:
            change = metric.value - latest.value
            if latest.value != 0:
                change_pct = (change / abs(latest.value)) * 100
            
            if change > 0:
                trend = "up"
            elif change < 0:
                trend = "down"
            else:
                trend = "stable"
        
        return await repo.upsert(
            indicator_id=metric.metric_id,
            name=metric.name or metric.metric_id,
            value=metric.value,
            unit=metric.unit,
            category=category,
            source=metric.source,
            name_vi=metric.name_vi,
            source_url=metric.source_url,
            change=change,
            change_pct=change_pct,
            trend=trend,
            attributes=self._serialize_attributes(metric.attributes),
        )
    
    @staticmethod
    def _serialize_attributes(attrs: dict = None) -> str:
        """Serialize attributes dict to JSON string for storage."""
        if not attrs:
            return None
        import json
        # Filter out None values and non-serializable types
        clean = {}
        for k, v in attrs.items():
            if v is not None:
                try:
                    json.dumps(v)
                    clean[k] = v
                except (TypeError, ValueError):
                    clean[k] = str(v)
        return json.dumps(clean, ensure_ascii=False) if clean else None
    
    def _get_indicator_category(self, metric_type) -> str:
        """Map metric type to indicator category.
        
        Args:
            metric_type: MetricType enum or string. Uses .value for enum lookup.
        """
        mapping = {
            "exchange_rate": "vietnam_forex",
            "interbank_rate": "vietnam_monetary",
            "policy_rate": "vietnam_monetary",
            "gold_price": "vietnam_commodity",
            "cpi": "vietnam_inflation",
            "omo": "vietnam_monetary",
            "credit": "vietnam_credit",
            "index": "global_macro",
            "bond_yield": "global_macro",
            "commodity": "global_commodity",
        }
        # MetricType is a str Enum: str(MetricType.X) = "MetricType.X", not "x"
        # Use .value to get the raw string for dict lookup
        key = metric_type.value if hasattr(metric_type, 'value') else str(metric_type)
        return mapping.get(key, "other")
    
    def _compute_hash(self, event: EventRecord) -> str:
        """Compute hash for event deduplication."""
        # Hash based on title + source + first 200 chars of content
        content_preview = (event.content or event.summary or "")[:200]
        text = f"{event.title}|{event.source}|{content_preview}"
        return hashlib.md5(text.encode()).hexdigest()
    
    def _event_to_dict(self, event: EventRecord) -> dict:
        """Convert EventRecord to dict for LLM processing."""
        return {
            "title": event.title,
            "summary": event.summary,
            "content": event.content,
            "source": event.source,
            "source_url": event.source_url,
            "published_at": event.published_at.isoformat() if event.published_at else None,
            "language": event.language,
        }
    
    def _db_event_to_dict(self, event) -> dict:
        """Convert database Event model to dict for ranker."""
        return {
            "id": event.id,
            "title": event.title,
            "base_score": event.base_score,
            "current_score": event.current_score,
            "published_at": event.published_at.isoformat() if event.published_at else None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "linked_indicators": event.linked_indicators or [],
            "is_follow_up": event.is_follow_up,
            "follows_up_on": event.follows_up_on,
            "category": event.category,
            "is_market_relevant": event.is_market_relevant,
        }
    
    def _build_context_summary(
        self,
        active_signals: list,
        active_themes: list,
        indicator_trends: dict,
        lookback_days: int
    ) -> str:
        """Build a simple context summary for scoring."""
        lines = [f"Context from last {lookback_days} days:"]
        
        if active_signals:
            lines.append(f"\nActive Signals ({len(active_signals)}):")
            for sig in active_signals[:10]:  # Limit to 10
                direction = sig.get('direction', '?')
                indicator = sig.get('target_indicator', 'unknown')
                lines.append(f"  - [{sig.get('confidence', 'medium')}] {sig['prediction']} (target: {indicator} {direction})")
        
        if active_themes:
            lines.append(f"\nActive Themes ({len(active_themes)}):")
            for theme in active_themes[:5]:  # Limit to 5
                lines.append(f"  - {theme['name']} (strength: {theme.get('strength', 0)}, events: {theme.get('event_count', 0)})")
        
        if indicator_trends:
            lines.append(f"\nIndicator Trends:")
            for ind_id, trend in list(indicator_trends.items()):
                lines.append(f"  - {ind_id}: {trend['trend']} ({trend['change_pct']:.2f}%)")
        
        return "\n".join(lines)
    
    def _generate_run_summary(self, results: dict) -> str:
        """Generate a human-readable run summary."""
        steps = results.get("steps", {})
        
        lines = [
            f"Pipeline run {results['run_id']}:",
            f"- Crawled {len(steps.get('crawl', {}).get('sources', []))} sources",
            f"- {steps.get('metrics', {}).get('indicators_updated', 0)} indicators updated",
            f"- {steps.get('classify', {}).get('relevant', 0)}/{steps.get('classify', {}).get('total', 0)} news relevant",
            f"- {steps.get('save', {}).get('events_saved', 0)} events saved",
            f"- {steps.get('save', {}).get('signals_created', 0)} signals created, {steps.get('save', {}).get('themes_updated', 0)} themes updated",
            f"- {steps.get('rank', {}).get('key_events', 0)} key events, {steps.get('rank', {}).get('other_news', 0)} other news",
            f"- {steps.get('watchlist', {}).get('triggered', 0)} watchlist items triggered"
        ]
        
        return "\n".join(lines)
    
    async def run_ranking_only(self) -> dict:
        """Run only the ranking layer (for scheduled decay updates)."""
        logger.info("Running ranking only...")
        
        await init_engine()
        
        async with get_session() as session:
            events_repo = EventRepository(session)
            themes_repo = ThemeRepository(session)
            
            all_active = await events_repo.get_active_events(max_age_days=30)
            all_active_dicts = [self._db_event_to_dict(e) for e in all_active]
            
            hot_topics = self.ranker.detect_hot_topics(all_active_dicts)
            hot_topic_names = [t["topic"] for t in hot_topics]
            
            active_themes = await themes_repo.get_active_and_emerging()
            active_theme_names = [t.name for t in active_themes]
            
            ranking_result = self.ranker.rank_all_events(
                all_active_dicts,
                active_themes=active_theme_names,
                hot_topics=hot_topic_names,
            )
            
            for r in ranking_result.get("rankings", []):
                await events_repo.update_scores(
                    event_id=r["event_id"],
                    base_score=r.get("original_score", 50),
                    current_score=r["final_score"],
                    decay_factor=r["decay_factor"],
                    boost_factor=r["boost_factor"],
                    display_section=r["display_section"],
                )
        
        return ranking_result


# ============================================
# CLI ENTRY POINT
# ============================================

def main():
    """Run the pipeline from command line."""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Run Market Intelligence Pipeline")
    parser.add_argument("--rank-only", action="store_true", help="Run ranking only")
    
    args = parser.parse_args()
    
    pipeline = Pipeline()
    
    if args.rank_only:
        result = asyncio.run(pipeline.run_ranking_only())
    else:
        result = asyncio.run(pipeline.run())
    
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
