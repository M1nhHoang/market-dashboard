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
7. Review investigations
8. Save run history
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
    InvestigationRepository,
    RunHistoryRepository,
)
from data_transformers import CrawlerOutput
from data_transformers.models import MetricRecord, EventRecord, CalendarRecord

from .classifier import Classifier
from .scorer import Scorer
from .ranker import Ranker, InvestigationReviewer
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
        self.investigation_reviewer = InvestigationReviewer()
        
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
                investigations_repo = InvestigationRepository(session)
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
                
                # Get open investigations
                open_investigations = await investigations_repo.get_open()
                open_investigations_list = [
                    {
                        "id": inv.id,
                        "question": inv.question,
                        "priority": inv.priority,
                        "evidence_count": inv.evidence_count,
                    }
                    for inv in open_investigations
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
                    open_investigations_list,
                    indicator_trends,
                    self.lookback_days
                )
                
                results["steps"]["context"] = {
                    "open_investigations": len(open_investigations_list),
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
                            open_investigations=open_investigations_list,
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
                investigations_created = 0
                predictions_created = 0
                
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
                                needs_investigation=causal_analysis.get("needs_investigation", []),
                                affected_indicators=classification.linked_indicators or [],
                                reasoning=causal_analysis.get("reasoning"),
                            )
                        
                        # Handle investigation actions
                        if scoring and scoring.investigation_action:
                            inv_action = scoring.investigation_action
                            
                            # Create new investigation
                            if inv_action.get("creates_new"):
                                new_inv = inv_action.get("new_investigation", {})
                                if new_inv.get("question"):
                                    await investigations_repo.create_investigation(
                                        question=new_inv.get("question"),
                                        source_event_id=new_event.id,
                                        priority=new_inv.get("priority", "medium"),
                                        context=new_inv.get("what_to_look_for"),
                                        related_indicators=classification.linked_indicators or [],
                                    )
                                    investigations_created += 1
                            
                            # Resolve existing investigation
                            if inv_action.get("resolves"):
                                await investigations_repo.resolve(
                                    investigation_id=inv_action["resolves"],
                                    resolution=inv_action.get("resolution", ""),
                                    confidence="medium",
                                    resolved_by_event_id=new_event.id,
                                )
                        
                        # Save predictions
                        if scoring and scoring.predictions:
                            for pred in scoring.predictions:
                                if pred.get("prediction"):
                                    check_date = None
                                    if pred.get("check_by_date"):
                                        try:
                                            check_date = datetime.fromisoformat(pred["check_by_date"]).date()
                                        except:
                                            pass
                                    
                                    await investigations_repo.create_prediction(
                                        prediction=pred.get("prediction"),
                                        source_event_id=new_event.id,
                                        confidence=pred.get("confidence", "medium"),
                                        check_by_date=check_date,
                                        verification_indicator=pred.get("verification_indicator"),
                                    )
                                    predictions_created += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to save event {event.title[:50]}: {e}")
                
                results["steps"]["save"] = {
                    "events_saved": events_saved,
                    "investigations_created": investigations_created,
                    "predictions_created": predictions_created,
                }
                logger.info(f"Saved {events_saved} events, {investigations_created} investigations, {predictions_created} predictions")
                
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
                
                # Get open investigation IDs
                open_inv_ids = [inv.id for inv in open_investigations]
                
                # Rank events
                ranking_result = self.ranker.rank_all_events(
                    all_active_dicts,
                    open_investigation_ids=open_inv_ids,
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
                # Step 10: Review investigations
                # ============================================
                logger.info("Step 10: Reviewing investigations...")
                
                updates_applied = 0
                if open_investigations and scored_events:
                    try:
                        review_result = self.investigation_reviewer.review(
                            [{"id": inv.id, "question": inv.question} for inv in open_investigations],
                            [self._event_to_dict(se["event"]) for se in scored_events],
                        )
                        
                        for update in review_result.get("investigation_updates", []):
                            inv_id = update.get("investigation_id")
                            new_status = update.get("new_status")
                            
                            if new_status and new_status != "open":
                                await investigations_repo.update_status(
                                    investigation_id=inv_id,
                                    status=new_status,
                                )
                                updates_applied += 1
                            
                            # Add evidence
                            for evidence in update.get("evidence_today", []):
                                await investigations_repo.add_evidence(
                                    investigation_id=inv_id,
                                    event_id=evidence.get("event_id", ""),
                                    evidence_type=evidence.get("evidence_type", "neutral"),
                                    summary=evidence.get("summary", ""),
                                )
                    except Exception as e:
                        logger.error(f"Investigation review failed: {e}")
                
                results["steps"]["review"] = {
                    "investigations_reviewed": len(open_investigations),
                    "updates_applied": updates_applied,
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
                    investigations_opened=investigations_created,
                    investigations_updated=updates_applied,
                    investigations_resolved=0,  # TODO: track
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
            raw_result = await crawler.fetch()
            
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
        open_investigations: list,
        indicator_trends: dict,
        lookback_days: int
    ) -> str:
        """Build a simple context summary for scoring."""
        lines = [f"Context from last {lookback_days} days:"]
        
        if open_investigations:
            lines.append(f"\nOpen Investigations ({len(open_investigations)}):")
            for inv in open_investigations[:5]:
                lines.append(f"  - [{inv['priority']}] {inv['question']}")
        
        if indicator_trends:
            lines.append(f"\nIndicator Trends:")
            for ind_id, trend in list(indicator_trends.items())[:10]:
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
            f"- {steps.get('save', {}).get('investigations_created', 0)} investigations created",
            f"- {steps.get('rank', {}).get('key_events', 0)} key events, {steps.get('rank', {}).get('other_news', 0)} other news"
        ]
        
        return "\n".join(lines)
    
    async def run_ranking_only(self) -> dict:
        """Run only the ranking layer (for scheduled decay updates)."""
        logger.info("Running ranking only...")
        
        await init_engine()
        
        async with get_session() as session:
            events_repo = EventRepository(session)
            investigations_repo = InvestigationRepository(session)
            
            all_active = await events_repo.get_active_events(max_age_days=30)
            all_active_dicts = [self._db_event_to_dict(e) for e in all_active]
            
            hot_topics = self.ranker.detect_hot_topics(all_active_dicts)
            hot_topic_names = [t["topic"] for t in hot_topics]
            
            open_investigations = await investigations_repo.get_open()
            open_inv_ids = [inv.id for inv in open_investigations]
            
            ranking_result = self.ranker.rank_all_events(
                all_active_dicts,
                open_investigation_ids=open_inv_ids,
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
