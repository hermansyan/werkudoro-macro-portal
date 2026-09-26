import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.collectors.indicators import sync_indicators
from app.collectors.cross_asset import sync_cross_asset
from app.collectors.opportunity_radar import build_opportunity_radar
from app.collectors.news_rss import sync_rss_news
from app.collectors.briefing import sync_calendar, update_macro_briefing

logger = logging.getLogger("macro.scheduler")

scheduler = BackgroundScheduler()

def run_all_jobs():
    logger.info("Executing scheduled macro data sync...")
    try:
        sync_indicators()
    except Exception as e:
        logger.error(f"Error syncing indicators: {e}")

    try:
        sync_cross_asset()
        build_opportunity_radar()
    except Exception as e:
        logger.error(f"Error syncing cross-asset / opportunity radar metrics: {e}")
        
    try:
        sync_rss_news()
    except Exception as e:
        logger.error(f"Error syncing RSS news: {e}")
        
    try:
        sync_calendar()
        update_macro_briefing()
    except Exception as e:
        logger.error(f"Error syncing briefing: {e}")
        
    logger.info("Macro data synchronization finished.")

def start_scheduler():
    # Run every 15 minutes
    scheduler.add_job(run_all_jobs, "interval", minutes=15, id="macro_sync_job", replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started (interval: 15 min).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.")
