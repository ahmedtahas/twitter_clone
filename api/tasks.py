from celery import shared_task
from django.utils import timezone
import requests
from .models import Tweet, UserProfile
from datetime import timedelta

@shared_task
def fetch_and_update_tweets():
    response = requests.get('https://jsonplaceholder.typicode.com/posts')
    data = response.json()
    for item in data:
        user_profile, _ = UserProfile.objects.get_or_create(user_id=item['userId'])
        Tweet.objects.update_or_create(
            id=item['id'],
            defaults={
                'content': item['body'],
                'created_at': timezone.now(),
                'author': user_profile
            }
        )

import os
from django.conf import settings

@shared_task
def backup_and_delete_old_tweets():
    backup_period_days = settings.BACKUP_PERIOD_DAYS
    old_tweets = Tweet.objects.filter(created_at__lt=timezone.now() - timedelta(days=backup_period_days))
    with open('backup_tweets.txt', 'a') as file:
        for tweet in old_tweets:
            file.write(f"{tweet.id}, {tweet.content}\n")
            tweet.delete()