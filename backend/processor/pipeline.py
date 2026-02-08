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

from .classifier import Classifier
from .scorer import Scorer
from .ranker import Ranker
from .context_builder import ContextBuilder


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
        
    async def run(self) -> dict:
        """
        Run the complete pipeline.
        
        Returns:
            Dict with run results and statistics
        """
        run_start = datetime.now()
        run_id = run_start.strftime("%Y%m%d_%H%M%S")
        run_date = date.today()
        
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
            # Step 1: Crawl data from sources
            # ============================================
            logger.info("Step 1: Crawling data from sources...")
            
            crawler_outputs = await self._crawl_all_sources()
            
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
                # Step 5: Layer 1 - Classification + Dedup
                # ============================================
                logger.info("Step 5: Layer 1 - Classification...")
                
                classified_events = []
                duplicates_skipped = 0
                irrelevant_skipped = 0
                
                for event in all_events:
                    # Compute hash for deduplication
                    hash_value = self._compute_hash(event)
                    
                    # Check if already exists
                    existing = await events_repo.find_by_hash(hash_value)
                    if existing:
                        duplicates_skipped += 1
                        logger.debug(f"Skipping duplicate: {event.title[:50]}...")
                        continue
                    
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
                    "duplicates_skipped": duplicates_skipped,
                    "irrelevant_skipped": irrelevant_skipped,
                }
                logger.info(f"Classification: {len(classified_events)}/{len(all_events)} relevant (skipped {duplicates_skipped} dupes)")
                
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
                        # Create event
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
                            if sig_out.get("creates_new"):
                                new_sig = sig_out.get("new_signal", {})
                                if new_sig.get("prediction"):
                                    expires_at = None
                                    if new_sig.get("timeframe_days"):
                                        expires_at = datetime.now() + timedelta(days=new_sig["timeframe_days"])
                                    
                                    await signals_repo.create_signal(
                                        prediction=new_sig.get("prediction"),
                                        source_event_id=new_event.id,
                                        target_indicator=new_sig.get("target_indicator"),
                                        target_range_low=new_sig.get("target_range_low"),
                                        target_range_high=new_sig.get("target_range_high"),
                                        direction=new_sig.get("direction"),
                                        confidence=new_sig.get("confidence", "medium"),
                                        timeframe_days=new_sig.get("timeframe_days"),
                                        expires_at=expires_at,
                                        reasoning=new_sig.get("reasoning"),
                                        related_indicators=classification.linked_indicators or [],
                                    )
                                    signals_created += 1
                        
                        # Handle theme link from scoring
                        if scoring and scoring.theme_link:
                            theme_link = scoring.theme_link
                            theme_name = theme_link.get("theme_name")
                            if theme_name:
                                # Try to find existing theme
                                existing_theme = await themes_repo.get_by_name(theme_name)
                                if existing_theme:
                                    # Add event to existing theme
                                    await themes_repo.add_event(existing_theme.id, new_event.id)
                                    themes_updated += 1
                                elif theme_link.get("creates_new"):
                                    # Create new theme
                                    await themes_repo.create_theme(
                                        name=theme_name,
                                        event_id=new_event.id,
                                        initial_strength=theme_link.get("strength", 50),
                                    )
                                    themes_updated += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to save event {event.title[:50]}: {e}")
                
                results["steps"]["save"] = {
                    "events_saved": events_saved,
                    "signals_created": signals_created,
                    "themes_updated": themes_updated,
                }
                logger.info(f"Saved {events_saved} events, {signals_created} signals, {themes_updated} themes")
                
                # ============================================
                # Step 9: Layer 3 - Rank all active events
                # ============================================
                logger.info("Step 9: Layer 3 - Ranking all active events...")
                
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
                        # Check if keyword appears in today's events
                        keyword = item.trigger_condition
                        for se in scored_events:
                            event = se["event"]
                            if keyword.lower() in (event.title or "").lower() or keyword.lower() in (event.content or "").lower():
                                triggered = True
                                trigger_event_id = event.id if hasattr(event, 'id') else None
                                break
                    
                    elif item.trigger_type == "indicator":
                        # Check indicator threshold
                        triggered = await watchlist_repo.check_indicator_trigger(
                            item.id, 
                            indicators_repo
                        )
                    
                    elif item.trigger_type == "date":
                        # Check if trigger date reached
                        if item.trigger_value:
                            try:
                                trigger_date = datetime.fromisoformat(item.trigger_value).date()
                                if date.today() >= trigger_date:
                                    triggered = True
                            except:
                                pass
                    
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
    
    async def _crawl_all_sources(self) -> List[CrawlerOutput]:
        """Crawl all configured sources and return transformed outputs."""
        from crawlers import SBVCrawler
        
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
                save_raw=False       # Save raw output to data/raw for debugging
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
        
        # TODO: Add more crawlers here (News, Global, Calendar)
        
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
        )
    
    def _get_indicator_category(self, metric_type: str) -> str:
        """Map metric type to indicator category."""
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
        return mapping.get(str(metric_type), "other")
    
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
