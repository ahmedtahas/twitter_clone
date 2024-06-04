from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter_clone.settings')

app = Celery('twitter_clone')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'fetch-and-update-tweets-every-5-minutes': {
        'task': 'api.tasks.fetch_and_update_tweets',
        'schedule': crontab(minute='*/5'),
    },
    'backup-and-delete-old-tweets': {
        'task': 'api.tasks.backup_and_delete_old_tweets',
        'schedule': crontab(day_of_month=f'*/{int(os.getenv("BACKUP_PERIOD_DAYS", "30"))}'),
    },
}