"""
LLM Pipeline - Main orchestrator for the 3-layer analysis pipeline.

Pipeline Flow:
1. Load raw data from crawlers
2. Transform data (indicators → DB, news → for classification)
3. Layer 1: Classify news (relevant vs irrelevant)
4. Layer 2: Score relevant news (with context)
5. Layer 3: Rank all active events
6. Review investigations
7. Save results and run history
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger

from config import settings
from database import init_database
from dao import get_db, DatabaseConnection
from .classifier import Classifier, classify_indicator_data
from .scorer import Scorer, generate_context_summary
from .ranker import Ranker, InvestigationReviewer
from .data_transformer import DataTransformer, load_raw_data
from .context_builder import ContextBuilder


class Pipeline:
    """
    Main pipeline orchestrator.
    
    Coordinates all layers and manages data flow between them.
    """
    
    def __init__(
        self, 
        db_path: Path = None,
        data_dir: Path = None,
        lookback_days: int = 7
    ):
        self.db_path = db_path or settings.DATABASE_PATH
        self.data_dir = data_dir or settings.DATA_DIR
        self.lookback_days = lookback_days
        
        # Ensure database exists
        init_database(self.db_path)
        
        # Initialize components
        self.db = get_db(self.db_path)
        self.transformer = DataTransformer(self.db)
        self.context_builder = ContextBuilder(self.db_path)
        self.classifier = Classifier()
        self.scorer = Scorer()
        self.ranker = Ranker()
        self.investigation_reviewer = InvestigationReviewer()
        
    def run(
        self,
        source_file: Path = None,
        skip_classification: bool = False,
        skip_scoring: bool = False,
        skip_ranking: bool = False
    ) -> dict:
        """
        Run the complete pipeline.
        
        Args:
            source_file: Path to raw data JSON (defaults to latest sbv_source_output.json)
            skip_classification: Skip Layer 1 (for debugging)
            skip_scoring: Skip Layer 2 (for debugging)
            skip_ranking: Skip Layer 3 (for debugging)
            
        Returns:
            Dict with run results and statistics
        """
        run_start = datetime.now()
        run_id = run_start.strftime("%Y%m%d_%H%M%S")
        run_date = run_start.strftime("%Y-%m-%d")
        
        logger.info(f"=== Starting Pipeline Run {run_id} ===")
        
        results = {
            "run_id": run_id,
            "run_date": run_date,
            "status": "in_progress",
            "steps": {}
        }
        
        try:
            # ============================================
            # Step 1: Load raw data
            # ============================================
            logger.info("Step 1: Loading raw data...")
            
            source_file = source_file or (self.data_dir / "raw" / "sbv_source_output.json")
            raw_data = load_raw_data(source_file)
            
            results["steps"]["load_data"] = {
                "source": str(source_file),
                "items": len(raw_data.get('data', [])),
                "crawled_at": raw_data.get('crawled_at')
            }
            logger.info(f"Loaded {len(raw_data.get('data', []))} items from {source_file}")
            
            # ============================================
            # Step 2: Transform and save indicators
            # ============================================
            logger.info("Step 2: Transforming data...")
            
            transform_result = self.transformer.process_sbv_data(raw_data)
            news_items = transform_result["news_items"]
            
            results["steps"]["transform"] = transform_result["stats"]
            logger.info(f"Transform stats: {transform_result['stats']}")
            
            # ============================================
            # Step 3: Layer 1 - Classify news
            # ============================================
            if skip_classification:
                logger.info("Step 3: Skipping classification...")
                classified_news = news_items  # Pass through without classification
            else:
                logger.info(f"Step 3: Classifying {len(news_items)} news items...")
                
                classified_news = self.classifier.classify_batch(news_items)
                relevant_news = self.classifier.filter_relevant(classified_news)
                
                results["steps"]["classify"] = {
                    "total": len(news_items),
                    "relevant": len(relevant_news),
                    "irrelevant": len(news_items) - len(relevant_news)
                }
                logger.info(f"Classification: {len(relevant_news)}/{len(news_items)} relevant")
            
            # ============================================
            # Step 4: Build context for scoring
            # ============================================
            logger.info("Step 4: Building context...")
            
            previous_context = self.context_builder.build_previous_context(self.lookback_days)
            context_text = self.context_builder.format_for_prompt(previous_context)
            
            # Generate context summary
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            context_summary = generate_context_summary(
                client, 
                settings.LLM_MODEL,
                context_text, 
                self.lookback_days
            )
            
            open_investigations = previous_context.get("open_investigations", [])
            
            results["steps"]["context"] = {
                "open_investigations": len(open_investigations),
                "lookback_days": self.lookback_days
            }
            
            # ============================================
            # Step 5: Layer 2 - Score relevant news
            # ============================================
            if skip_scoring:
                logger.info("Step 5: Skipping scoring...")
                scored_news = relevant_news
            else:
                relevant_news = [n for n in classified_news if n.get('is_market_relevant', True)]
                
                if relevant_news:
                    logger.info(f"Step 5: Scoring {len(relevant_news)} relevant items...")
                    
                    scored_news = self.scorer.score_batch(
                        relevant_news,
                        previous_context_summary=context_summary,
                        open_investigations=open_investigations,
                        lookback_days=self.lookback_days
                    )
                    
                    results["steps"]["score"] = {
                        "scored": len(scored_news),
                        "avg_score": sum(n.get('base_score', 0) for n in scored_news) / len(scored_news) if scored_news else 0
                    }
                else:
                    logger.info("Step 5: No relevant news to score")
                    scored_news = []
                    results["steps"]["score"] = {"scored": 0, "avg_score": 0}
            
            # ============================================
            # Step 6: Save scored events to database
            # ============================================
            logger.info("Step 6: Saving events...")
            
            events_saved = 0
            investigations_created = 0
            predictions_created = 0
            
            for item in scored_news:
                # Create event
                event_id = f"evt_{run_id}_{events_saved:04d}"
                event = {
                    "id": event_id,
                    "title": item.get('title'),
                    "summary": item.get('summary'),
                    "content": item.get('content'),
                    "source": item.get('source'),
                    "source_url": item.get('source_url'),
                    "is_market_relevant": item.get('is_market_relevant', True),
                    "category": item.get('category'),
                    "region": "vietnam",
                    "linked_indicators": item.get('linked_indicators', []),
                    "base_score": item.get('base_score', 50),
                    "score_factors": item.get('score_factors', {}),
                    "current_score": item.get('base_score', 50),
                    "is_follow_up": item.get('is_follow_up', False),
                    "follows_up_on": item.get('follows_up_on'),
                    "published_at": item.get('published_at'),
                    "run_date": run_date,
                    "hash": item.get('hash')
                }
                
                try:
                    self.db.events.create(event)
                    events_saved += 1
                except Exception as e:
                    logger.warning(f"Failed to save event: {e}")
                    continue
                
                # Save causal analysis
                causal = item.get('causal_analysis', {})
                if causal and causal.get('chain'):
                    self.db.events.create_causal_analysis({
                        "event_id": event_id,
                        "template_id": causal.get('matched_template_id'),
                        "chain_steps": causal.get('chain', []),
                        "confidence": causal.get('confidence'),
                        "needs_investigation": causal.get('needs_investigation', []),
                        "affected_indicators": item.get('linked_indicators', []),
                        "reasoning": causal.get('reasoning')
                    })
                
                # Handle investigation actions
                inv_action = item.get('investigation_action', {})
                
                if inv_action.get('creates_new'):
                    new_inv = inv_action.get('new_investigation', {})
                    if new_inv.get('question'):
                        self.db.investigations.create(
                            question=new_inv.get('question'),
                            source_event_id=event_id,
                            priority=new_inv.get('priority', 'medium'),
                            context=new_inv.get('what_to_look_for'),
                            related_indicators=item.get('linked_indicators', [])
                        )
                        investigations_created += 1
                
                if inv_action.get('resolves'):
                    self.db.investigations.update_status(
                        investigation_id=inv_action['resolves'],
                        status='resolved',
                        resolution=inv_action.get('resolution'),
                        resolved_by_event_id=event_id
                    )
                
                # Save predictions
                for pred in item.get('predictions', []):
                    if pred.get('prediction'):
                        self.db.investigations.create_prediction({
                            "prediction": pred.get('prediction'),
                            "based_on_events": [event_id],
                            "source_event_id": event_id,
                            "confidence": pred.get('confidence'),
                            "check_by_date": pred.get('check_by_date'),
                            "verification_indicator": pred.get('verification_indicator')
                        })
                        predictions_created += 1
            
            results["steps"]["save"] = {
                "events": events_saved,
                "investigations_created": investigations_created,
                "predictions": predictions_created
            }
            
            # ============================================
            # Step 7: Layer 3 - Rank all active events
            # ============================================
            if skip_ranking:
                logger.info("Step 7: Skipping ranking...")
            else:
                logger.info("Step 7: Ranking all active events...")
                
                # Get all active events (convert entities to dicts for ranker)
                all_active = [e.to_dict() for e in self.db.events.get_active_events(max_age_days=30)]
                
                # Detect hot topics
                hot_topics = self.ranker.detect_hot_topics(all_active)
                hot_topic_names = [t['topic'] for t in hot_topics]
                
                # Get open investigation IDs
                open_inv_ids = [inv.id for inv in open_investigations]
                
                # Rank events
                ranking_result = self.ranker.rank_all_events(
                    all_active,
                    open_investigation_ids=open_inv_ids,
                    hot_topics=hot_topic_names
                )
                
                # Update events in database
                for r in ranking_result['rankings']:
                    self.db.events.update_ranking(
                        event_id=r['event_id'],
                        current_score=r['final_score'],
                        decay_factor=r['decay_factor'],
                        boost_factor=r['boost_factor'],
                        display_section=r['display_section'],
                        hot_topic=r.get('hot_topic')
                    )
                
                results["steps"]["rank"] = {
                    "ranked": len(ranking_result['rankings']),
                    "hot_topics": len(hot_topics),
                    **ranking_result['section_summary']
                }
            
            # ============================================
            # Step 8: Review investigations
            # ============================================
            logger.info("Step 8: Reviewing investigations...")
            
            if open_investigations and scored_news:
                review_result = self.investigation_reviewer.review(
                    open_investigations,
                    scored_news
                )
                
                # Apply updates
                updates_applied = 0
                for update in review_result.get('investigation_updates', []):
                    inv_id = update.get('investigation_id')
                    new_status = update.get('new_status')
                    
                    if new_status and new_status != 'open':
                        self.db.investigations.update_status(
                            investigation_id=inv_id,
                            status=new_status,
                            evidence_summary=update.get('reasoning')
                        )
                        updates_applied += 1
                    
                    # Add evidence
                    for evidence in update.get('evidence_today', []):
                        self.db.investigations.add_evidence(
                            investigation_id=inv_id,
                            event_id=evidence.get('event_id'),
                            evidence_type=evidence.get('evidence_type'),
                            summary=evidence.get('summary')
                        )
                
                results["steps"]["review"] = {
                    "investigations_reviewed": len(open_investigations),
                    "updates_applied": updates_applied
                }
            else:
                results["steps"]["review"] = {"investigations_reviewed": 0, "updates_applied": 0}
            
            # ============================================
            # Step 9: Save run history
            # ============================================
            logger.info("Step 9: Saving run history...")
            
            summary = self._generate_run_summary(results)
            
            self.db.run_history.save_run(
                run_date=run_date,
                news_count=len(news_items),
                events_extracted=events_saved,
                events_key=results["steps"].get("rank", {}).get("key_events", 0),
                events_other=results["steps"].get("rank", {}).get("other_news", 0),
                investigations_opened=investigations_created,
                investigations_updated=results["steps"].get("review", {}).get("updates_applied", 0),
                investigations_resolved=0,  # TODO: track this
                summary=summary,
                status="success"
            )
            
            results["status"] = "success"
            results["summary"] = summary
            results["duration_seconds"] = (datetime.now() - run_start).total_seconds()
            
            logger.info(f"=== Pipeline Run Complete in {results['duration_seconds']:.1f}s ===")
            logger.info(summary)
            
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            
            # Save failed run
            self.db.run_history.save_run(
                run_date=run_date,
                news_count=0,
                events_extracted=0,
                events_key=0,
                events_other=0,
                investigations_opened=0,
                investigations_updated=0,
                investigations_resolved=0,
                summary=f"Pipeline failed: {str(e)}",
                status="failed"
            )
        
        return results
    
    def _generate_run_summary(self, results: dict) -> str:
        """Generate a human-readable run summary."""
        steps = results.get("steps", {})
        
        lines = [
            f"Pipeline run {results['run_id']}:",
            f"- Loaded {steps.get('load_data', {}).get('items', 0)} items",
            f"- {steps.get('transform', {}).get('indicators_updated', 0)} indicators updated",
            f"- {steps.get('classify', {}).get('relevant', 0)}/{steps.get('classify', {}).get('total', 0)} news relevant",
            f"- {steps.get('save', {}).get('events', 0)} events saved",
            f"- {steps.get('save', {}).get('investigations_created', 0)} investigations created",
            f"- {steps.get('rank', {}).get('key_events', 0)} key events, {steps.get('rank', {}).get('other_news', 0)} other news"
        ]
        
        return "\n".join(lines)
    
    def run_ranking_only(self) -> dict:
        """Run only the ranking layer (for scheduled decay updates)."""
        logger.info("Running ranking only...")
        
        # Convert entities to dicts for ranker
        all_active = [e.to_dict() for e in self.db.events.get_active_events(max_age_days=30)]
        hot_topics = self.ranker.detect_hot_topics(all_active)
        hot_topic_names = [t['topic'] for t in hot_topics]
        
        open_investigations = self.db.investigations.get_open()
        open_inv_ids = [inv.id for inv in open_investigations]
        
        ranking_result = self.ranker.rank_all_events(
            all_active,
            open_investigation_ids=open_inv_ids,
            hot_topics=hot_topic_names
        )
        
        for r in ranking_result['rankings']:
            self.db.events.update_ranking(
                event_id=r['event_id'],
                current_score=r['final_score'],
                decay_factor=r['decay_factor'],
                boost_factor=r['boost_factor'],
                display_section=r['display_section'],
                hot_topic=r.get('hot_topic')
            )
        
        return ranking_result


# ============================================
# CLI ENTRY POINT
# ============================================

def main():
    """Run the pipeline from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Market Intelligence Pipeline")
    parser.add_argument("--source", type=str, help="Path to source JSON file")
    parser.add_argument("--skip-classify", action="store_true", help="Skip classification")
    parser.add_argument("--skip-score", action="store_true", help="Skip scoring")
    parser.add_argument("--skip-rank", action="store_true", help="Skip ranking")
    parser.add_argument("--rank-only", action="store_true", help="Run ranking only")
    
    args = parser.parse_args()
    
    pipeline = Pipeline()
    
    if args.rank_only:
        result = pipeline.run_ranking_only()
    else:
        source = Path(args.source) if args.source else None
        result = pipeline.run(
            source_file=source,
            skip_classification=args.skip_classify,
            skip_scoring=args.skip_score,
            skip_ranking=args.skip_rank
        )
    
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
