"""
Scheduler - Automated data collection and processing

Job Schedule:
1. SBV Data Crawl: Every 2 hours (primary data source)
2. Full Pipeline: Daily at 7:30 AM (before market open)
3. Ranking Refresh: Every hour (apply time decay)
4. News Crawl: Every hour (future - when news crawler is ready)
5. Global Indicators: Every 4 hours (future - when global crawler is ready)

Usage:
    python scheduler.py              # Run scheduler daemon
    python scheduler.py --once       # Run pipeline once and exit
    python scheduler.py --ranking    # Run ranking refresh only
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import settings, ensure_directories
from database import init_database, get_connection


class MarketIntelligenceScheduler:
    """
    Scheduler for automated data collection and processing.
    
    Integrates with the 3-Layer LLM Pipeline:
    - Layer 1: Classifier - Filter relevant news
    - Layer 2: Scorer - Score and analyze
    - Layer 3: Ranker - Apply decay and boost
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.data_dir = settings.DATA_DIR
        self._last_run_result = None
        
    def setup(self):
        """Setup scheduled jobs."""
        # Ensure directories exist
        ensure_directories()
        
        # Initialize database
        init_database(settings.DATABASE_PATH)
        
        # Job 1: SBV Data Crawl every 2 hours
        self.scheduler.add_job(
            self.crawl_sbv_data,
            IntervalTrigger(hours=2),
            id="crawl_sbv",
            name="Crawl SBV Data",
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(minutes=5)  # First run in 5 minutes
        )
        
        # Job 2: Full pipeline daily at 7:30 AM (before market)
        self.scheduler.add_job(
            self.run_full_pipeline,
            CronTrigger(hour=7, minute=30),
            id="daily_pipeline",
            name="Daily Full Pipeline",
            replace_existing=True
        )
        
        # Job 3: Ranking refresh every hour (apply time decay)
        self.scheduler.add_job(
            self.refresh_rankings,
            IntervalTrigger(hours=1),
            id="ranking_refresh",
            name="Hourly Ranking Refresh",
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(minutes=30)  # First run in 30 minutes
        )
        
        # Job 4: News crawl every hour (placeholder for future)
        self.scheduler.add_job(
            self.crawl_news,
            IntervalTrigger(hours=settings.CRAWLER_INTERVAL_HOURS),
            id="crawl_news",
            name="Crawl News Sources",
            replace_existing=True
        )
        
        # Job 5: Global indicators every 4 hours (placeholder for future)
        self.scheduler.add_job(
            self.update_global_indicators,
            IntervalTrigger(hours=4),
            id="update_global",
            name="Update Global Indicators",
            replace_existing=True
        )
        
        logger.info("Scheduler setup complete with 5 jobs")
        self._log_schedule()
        
    def _log_schedule(self):
        """Log current job schedule."""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            logger.info(f"  - {job.name}: {job.trigger}")
    
    async def crawl_sbv_data(self):
        """
        Job: Crawl SBV data (exchange rates, interbank rates, OMO).
        
        This is the primary data source currently implemented.
        """
        logger.info("Starting SBV data crawl...")
        
        try:
            from crawlers.sbv_crawler import SBVCrawler
            
            crawler = SBVCrawler(self.data_dir)
            result = await crawler.run()
            
            if result.success:
                logger.info(f"SBV crawl complete. Data saved to: {result.output_path}")
                return True
            else:
                logger.warning(f"SBV crawl failed: {result.error}")
                return False
                
        except ImportError:
            logger.warning("SBV crawler not found, skipping")
            return False
        except Exception as e:
            logger.exception(f"SBV crawl job failed: {e}")
            return False
    
    async def run_full_pipeline(self):
        """
        Job: Run the complete 3-Layer LLM Pipeline.
        
        Steps:
        1. Load raw data from crawlers
        2. Transform to database format
        3. Run Layer 1 (Classification)
        4. Run Layer 2 (Scoring)
        5. Run Layer 3 (Ranking)
        6. Save results to database
        """
        logger.info("Starting full pipeline run...")
        
        try:
            from processor.pipeline import Pipeline
            
            pipeline = Pipeline()
            result = pipeline.run()
            
            self._last_run_result = result
            
            if result.get("status") == "success":
                stats = result.get("stats", {})
                logger.info(f"Pipeline complete: {stats.get('classified_items', 0)} items classified, "
                           f"{stats.get('events_created', 0)} events created")
                return True
            else:
                logger.warning(f"Pipeline had issues: {result.get('error', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.exception(f"Pipeline run failed: {e}")
            return False
    
    async def refresh_rankings(self):
        """
        Job: Refresh rankings with time decay (Layer 3 only).
        
        This applies hourly decay to existing scores without re-running
        the full analysis. Efficient for keeping rankings fresh.
        """
        logger.info("Refreshing rankings with time decay...")
        
        try:
            from processor.ranker import Ranker
            
            ranker = Ranker()
            
            # Get events that need decay applied
            conn = get_connection(settings.DATABASE_PATH)
            cursor = conn.execute(
                """SELECT id, base_score, published_at, boost_factors 
                   FROM events 
                   WHERE display_section != 'archived'"""
            )
            events = cursor.fetchall()
            
            updated_count = 0
            for event in events:
                event_dict = dict(event)
                
                # Calculate new score with time decay
                import json
                boost_factors = json.loads(event_dict.get('boost_factors', '{}') or '{}')
                
                new_score = ranker._calculate_current_score(
                    base_score=event_dict.get('base_score', 50),
                    published_at=event_dict.get('published_at'),
                    boost_factors=boost_factors
                )
                
                # Determine new display section
                new_section = ranker._determine_display_section(new_score)
                
                # Update if changed
                conn.execute(
                    """UPDATE events 
                       SET current_score = ?, display_section = ?, updated_at = ?
                       WHERE id = ?""",
                    (new_score, new_section, datetime.now().isoformat(), event_dict['id'])
                )
                updated_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Rankings refreshed: {updated_count} events updated")
            return True
            
        except Exception as e:
            logger.exception(f"Ranking refresh failed: {e}")
            return False
    
    async def crawl_news(self):
        """Job: Crawl all news sources (placeholder for future implementation)."""
        logger.debug("News crawl job triggered (not yet implemented)")
        
        try:
            from crawlers.news_crawler import NewsCrawler
            
            crawler = NewsCrawler(self.data_dir)
            result = await crawler.run()
            
            if result.success:
                logger.info(f"News crawl complete: {len(result.data)} articles")
                return True
            else:
                logger.warning(f"News crawl partial/failed: {result.error}")
                return False
                
        except ImportError:
            logger.debug("News crawler not implemented yet")
            return False
        except Exception as e:
            logger.exception(f"News crawl job failed: {e}")
            return False
    
    async def update_global_indicators(self):
        """Job: Update global market indicators (placeholder for future)."""
        logger.debug("Global indicators job triggered (not yet implemented)")
        
        try:
            from crawlers.global_crawler import GlobalCrawler
            
            crawler = GlobalCrawler(self.data_dir)
            result = await crawler.run()
            
            if result.success:
                self._save_indicators(result.data)
                logger.info("Global indicators updated")
                return True
            else:
                logger.warning(f"Global update failed: {result.error}")
                return False
                
        except ImportError:
            logger.debug("Global crawler not implemented yet")
            return False
        except Exception as e:
            logger.exception(f"Global indicators job failed: {e}")
            return False
    
    def _save_indicators(self, indicators: list[dict]):
        """Save indicators to database."""
        from dao import get_db
        
        db = get_db(settings.DATABASE_PATH)
        for indicator in indicators:
            db.indicators.upsert(indicator)
        logger.info(f"Saved {len(indicators)} indicators to database")
    
    def start(self):
        """Start the scheduler."""
        self.setup()
        self.scheduler.start()
        logger.info("Scheduler started - Press Ctrl+C to stop")
        
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def run_once(self):
        """Run the full pipeline once and exit."""
        ensure_directories()
        init_database(settings.DATABASE_PATH)
        
        logger.info("Running pipeline once...")
        result = asyncio.get_event_loop().run_until_complete(self.run_full_pipeline())
        
        if result:
            logger.info("Pipeline completed successfully")
        else:
            logger.error("Pipeline failed")
        
        return result
    
    def run_ranking_only(self):
        """Run only the ranking refresh and exit."""
        ensure_directories()
        init_database(settings.DATABASE_PATH)
        
        logger.info("Running ranking refresh only...")
        result = asyncio.get_event_loop().run_until_complete(self.refresh_rankings())
        
        if result:
            logger.info("Ranking refresh completed successfully")
        else:
            logger.error("Ranking refresh failed")
        
        return result


def run_scheduler():
    """Run the scheduler as main process."""
    import signal
    
    scheduler = MarketIntelligenceScheduler()
    scheduler.start()
    
    # Handle graceful shutdown
    def shutdown(signum, frame):
        logger.info("Received shutdown signal")
        scheduler.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # Keep running
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()


def main():
    """Main entry point with CLI arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Market Intelligence Scheduler")
    parser.add_argument("--once", action="store_true", help="Run pipeline once and exit")
    parser.add_argument("--ranking", action="store_true", help="Run ranking refresh only")
    parser.add_argument("--crawl-sbv", action="store_true", help="Run SBV crawl only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")
    
    scheduler = MarketIntelligenceScheduler()
    
    if args.once:
        result = scheduler.run_once()
        sys.exit(0 if result else 1)
    elif args.ranking:
        result = scheduler.run_ranking_only()
        sys.exit(0 if result else 1)
    elif args.crawl_sbv:
        ensure_directories()
        result = asyncio.get_event_loop().run_until_complete(scheduler.crawl_sbv_data())
        sys.exit(0 if result else 1)
    else:
        # Run as daemon
        run_scheduler()


if __name__ == "__main__":
    main()
