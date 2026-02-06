"""
Scheduler - Automated data collection and processing

Current Setup:
- Full Pipeline runs every hour (configurable via CRAWLER_INTERVAL_HOURS)
- Pipeline includes: crawling → classification → scoring → ranking

Usage:
    python scheduler.py              # Run scheduler daemon
    python scheduler.py --once       # Run pipeline once and exit
"""
import asyncio
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings, ensure_directories
from utils import logger, init_logging


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
        """
        Setup scheduled jobs.
        
        Current setup: Single job runs full pipeline every hour.
        The pipeline internally handles: crawling → classification → scoring → ranking.
        
        NOTE: In the future, jobs can be split for more granular control:
        - Crawl jobs (SBV, News, Global) can run at different intervals
        - Ranking refresh can run more frequently (e.g., every 15 mins) 
        - Full LLM analysis can run less frequently (e.g., every 4 hours)
        
        For now, keeping it simple with a single unified pipeline job.
        """
        # Ensure directories exist
        ensure_directories()
        
        # NOTE: Database initialization is now handled by pipeline via init_engine()
        
        # Main job: Full pipeline every hour
        # This includes: crawling → classification → scoring → ranking
        self.scheduler.add_job(
            self.run_full_pipeline,
            IntervalTrigger(hours=settings.CRAWLER_INTERVAL_HOURS),
            id="full_pipeline",
            name="Full Pipeline (Crawl + Analyze + Rank)",
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(minutes=1)  # First run in 1 minute
        )
        
        logger.info("Scheduler setup complete with 1 job (full pipeline)")
        self._log_schedule()
        
    def _log_schedule(self):
        """Log current job schedule."""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            logger.info(f"  - {job.name}: {job.trigger}")
    
    async def run_full_pipeline(self):
        """
        Job: Run the complete 3-Layer LLM Pipeline.
        
        Steps:
        1. Crawl data from sources
        2. Transform to CrawlerOutput format
        3. Save metrics and calendar to database
        4. Run Layer 1 (Classification + Dedup)
        5. Run Layer 2 (Scoring with context)
        6. Run Layer 3 (Ranking with decay)
        7. Review investigations
        8. Save run history
        """
        logger.info("Starting full pipeline run...")
        
        try:
            from processor.pipeline import Pipeline
            
            pipeline = Pipeline()
            result = await pipeline.run()  # async call
            
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
        
        logger.info("Running pipeline once...")
        result = asyncio.run(self.run_full_pipeline())
        
        if result:
            logger.info("Pipeline completed successfully")
        else:
            logger.error("Pipeline failed")
        
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
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    init_logging(app_name="scheduler")
    if args.verbose:
        logger.info("Verbose mode enabled")
    
    # NOTE: Migrations are handled by backend service
    # Scheduler depends_on backend:service_healthy, so migrations are already done
    
    scheduler = MarketIntelligenceScheduler()
    
    if args.once:
        result = scheduler.run_once()
        sys.exit(0 if result else 1)
    else:
        # Run as daemon
        run_scheduler()


if __name__ == "__main__":
    main()
