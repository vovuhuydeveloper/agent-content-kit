"""
Celery application configuration
Task queue config and initialization
"""

import os

from celery import Celery
from celery.schedules import crontab

# Create Celery application
celery_app = Celery('autoclip')

# Configure Celery
class CeleryConfig:
    """Celery configuration class"""

    # Task serialization format
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True

    # Redis configuration
    broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Task configuration
    task_always_eager = os.getenv('CELERY_ALWAYS_EAGER', 'False').lower() == 'true'
    task_eager_propagates = True

    # Worker configuration
    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 1000
    worker_disable_rate_limits = True

    # Task routing
    task_routes = {
        'backend.tasks.processing.*': {'queue': 'processing'},
        'backend.tasks.video.*': {'queue': 'video'},
        'backend.tasks.notification.*': {'queue': 'notification'},
        'backend.tasks.upload.*': {'queue': 'upload'},
        'agents.*': {'queue': 'processing'},
    }

    # Periodic tasks
    beat_schedule = {
        'check-scheduled-jobs': {
            'task': 'schedule.check_scheduled_jobs',
            'schedule': crontab(minute='*'),
        },
        'collect-analytics': {
            'task': 'analytics.collect_all',
            'schedule': crontab(hour=6, minute=0),
        },
    }

    # Result configuration
    result_expires = 3600
    task_ignore_result = False

    # Logging
    worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
    worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'

# Apply configuration
celery_app.config_from_object(CeleryConfig)

# Set this as the default Celery app
celery_app.set_default()

# Auto-discover tasks (only existing modules)
celery_app.autodiscover_tasks([
    'backend.tasks.agent_tasks',
    'backend.tasks.schedule_tasks',
    'backend.tasks.analytics_collector',
    'backend.tasks.processing',
    'backend.tasks.video',
    'backend.tasks.notification',
])


# Start Telegram bot when worker is ready
@celery_app.on_after_finalize.connect
def setup_telegram_bot(sender, **kwargs):
    """Start Telegram bot polling in background thread"""
    try:
        from backend.telegram_bot import start_telegram_bot
        start_telegram_bot()
    except Exception as e:
        import logging
        logging.getLogger("celery").warning(f"Telegram bot start failed: {e}")


if __name__ == '__main__':
    celery_app.start()
