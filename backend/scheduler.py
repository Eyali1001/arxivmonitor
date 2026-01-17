from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from arxiv_collector import collector
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_sync():
    """Run scheduled sync job."""
    logger.info("Running scheduled sync...")
    await collector.quick_sync()
    logger.info("Scheduled sync completed")


def start_scheduler():
    """Start the background scheduler."""
    # Run quick sync daily at 6 AM UTC
    scheduler.add_job(
        scheduled_sync,
        CronTrigger(hour=6, minute=0),
        id="daily_sync",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
