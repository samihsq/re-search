from celery import Celery
from .config import settings

# Create Celery instance
celery_app = Celery(
    "stanford_opportunities",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.scraping_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "daily-scraping": {
        "task": "app.tasks.scraping_tasks.run_daily_scraping",
        "schedule": 86400.0,  # 24 hours in seconds
    },
    "cleanup-old-opportunities": {
        "task": "app.tasks.scraping_tasks.cleanup_old_opportunities",
        "schedule": 604800.0,  # 7 days in seconds
    },
}

if __name__ == "__main__":
    celery_app.start() 