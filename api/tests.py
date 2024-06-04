from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .views import calculate_deletion_statistics
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile, Tweet, Hashtag, Follow, Notification, Like, Retweet
from unittest.mock import patch
from .tasks import fetch_and_update_tweets, backup_and_delete_old_tweets
from django.conf import settings

class UserAuthenticationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='testpassword')
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_registration(self):
        response = self.client.post('/auth/register/', {
            'username': 'newuser',  
            'email': 'newuser@example.com',
            'password': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login(self):
        response = self.client.post('/auth/token/', {
            'username': 'testuser',  
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

class ActiveUsersTestCase(UserAuthenticationTestCase):
    def setUp(self):
        super().setUp()
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        self.user1.last_login = timezone.now() - timedelta(days=1)
        self.user1.save()

        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        self.user2.last_login = timezone.now() - timedelta(days=2)
        self.user2.save()

        self.user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')
        self.user3.last_login = timezone.now() - timedelta(hours=1)
        self.user3.save()

    def test_active_users_endpoint(self):
        response = self.client.get('/api/active-users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_usernames = ['user3', 'user1', 'user2']
        actual_usernames = [user['username'] for user in response.data]
        self.assertEqual(actual_usernames, expected_usernames)

class TweetTestCase(UserAuthenticationTestCase):
    def setUp(self):
        super().setUp()
        user_profile = UserProfile.objects.create(user=self.user, bio="Test bio")
        hashtag = Hashtag.objects.create(tag="world")
        tweet = Tweet.objects.create(content="Hello #world", author=user_profile)
        tweet.hashtags.add(hashtag)

        Tweet.objects.create(content="Tweet 1", author=user_profile, is_deleted=True, delete_reason="Spam", created_at=timezone.now() - timedelta(days=1))
        Tweet.objects.create(content="Tweet 2", author=user_profile, is_deleted=True, delete_reason="Spam", created_at=timezone.now() - timedelta(days=2))
        Tweet.objects.create(content="Tweet 3", author=user_profile, is_deleted=True, delete_reason="Inappropriate", created_at=timezone.now() - timedelta(days=3))
        Tweet.objects.create(content="Tweet 4", author=user_profile, is_deleted=False, delete_reason="", created_at=timezone.now() - timedelta(days=4))

    def test_deletion_statistics(self):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        stats = calculate_deletion_statistics(start_date, end_date)
        expected_stats = {'Spam': 2, 'Inappropriate': 1}
        self.assertEqual(stats, expected_stats)

class TweetDeletionTestCase(UserAuthenticationTestCase):
    def setUp(self):
        super().setUp()
        user_profile = UserProfile.objects.create(user=self.user, bio="Test bio")
        self.parent_tweet = Tweet.objects.create(content="Hello world", author=user_profile)
        self.reply_tweet = Tweet.objects.create(content="Hello back", author=user_profile, parent_tweet=self.parent_tweet)
        self.nested_reply_tweet = Tweet.objects.create(content="Hello again", author=user_profile, parent_tweet=self.reply_tweet)

    def test_recursive_deletion(self):
        self.parent_tweet.mark_as_deleted("Testing deletion")
        self.parent_tweet.refresh_from_db()
        self.reply_tweet.refresh_from_db()
        self.nested_reply_tweet.refresh_from_db()
        self.assertTrue(self.parent_tweet.is_deleted)
        self.assertTrue(self.reply_tweet.is_deleted)
        self.assertTrue(self.nested_reply_tweet.is_deleted)
        self.assertEqual(self.parent_tweet.delete_reason, "Testing deletion")
        self.assertEqual(self.reply_tweet.delete_reason, "Parent tweet deleted")
        self.assertEqual(self.nested_reply_tweet.delete_reason, "Parent tweet deleted")

class FollowTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpassword1')
        UserProfile.objects.create(user=self.user1)
        self.user2 = User.objects.create_user(username='user2', password='testpassword2')
        UserProfile.objects.create(user=self.user2)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def test_follow_user(self):
        response = self.client.post(f'/follow/{self.user2.username}/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unfollow_user(self):
        self.client.post(f'/follow/{self.user2.username}/')
        response = self.client.post(f'/unfollow/{self.user2.username}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

class FeedTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpassword1')
        UserProfile.objects.create(user=self.user1, bio="Bio for user1")  
        self.user2 = User.objects.create_user(username='user2', password='testpassword2')
        UserProfile.objects.create(user=self.user2, bio="Bio for user2")  
        self.user3 = User.objects.create_user(username='user3', password='testpassword3')
        UserProfile.objects.create(user=self.user3, bio="Bio for user3") 
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)
        
        Follow.objects.create(follower=self.user1.userprofile, followed=self.user2.userprofile)
        
        Tweet.objects.create(content="Hello from user2", author=self.user2.userprofile)
        Tweet.objects.create(content="Hello from user3", author=self.user3.userprofile)

    def test_feed_contents(self):
        response = self.client.get('/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Hello from user2", response.content.decode())
        self.assertNotIn("Hello from user3", response.content.decode())

class NotificationTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpassword1')
        UserProfile.objects.create(user=self.user1)
        self.user2 = User.objects.create_user(username='user2', password='testpassword2')
        UserProfile.objects.create(user=self.user2)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def test_notification_on_follow(self):
        self.client.post(f'/follow/{self.user2.username}/')
        notifications = Notification.objects.filter(recipient=self.user2.userprofile)
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().message, f"{self.user1.username} has started following you.")

class LikeRetweetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='testpassword')
        self.user_profile = UserProfile.objects.create(user=self.user)
        self.tweet = Tweet.objects.create(content="Hello world", author=self.user_profile)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_like_tweet(self):
        response = self.client.post(f'/like/{self.tweet.id}/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Like.objects.count(), 1)

    def test_retweet_tweet(self):
        response = self.client.post(f'/retweet/{self.tweet.id}/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Retweet.objects.count(), 1)

class CeleryTasksTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'testuser@example.com', 'password123')
        self.user_profile = UserProfile.objects.create(user=self.user)

    @patch('api.tasks.requests.get')
    def test_fetch_and_update_tweets(self, mock_get):
        mock_get.return_value.json.return_value = [
            {'userId': self.user.id, 'id': 1, 'body': 'Test tweet'}
        ]
        
        fetch_and_update_tweets.apply()  
        
        self.assertEqual(Tweet.objects.count(), 1)
        tweet = Tweet.objects.first()
        self.assertEqual(tweet.content, 'Test tweet')
        self.assertEqual(tweet.author, self.user_profile)

    def test_backup_and_delete_old_tweets(self):
        old_tweet = Tweet.objects.create(
            content='Old tweet',
            created_at=timezone.now() - timedelta(days=settings.BACKUP_PERIOD_DAYS + 10),  
            author=self.user_profile
        )
        backup_and_delete_old_tweets.apply()  
        
        self.assertFalse(Tweet.objects.filter(id=old_tweet.id).exists())
        with open('backup_tweets.txt', 'r') as file:
            print("hello")
            content = file.read()
            self.assertIn('Old tweet', content)

class TweetModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.user_profile = UserProfile.objects.create(user=self.user, bio="Test bio")

        self.tweet1 = Tweet.objects.create(content="Hello world! This is a test tweet.", author=self.user_profile)
        self.tweet2 = Tweet.objects.create(content="Another test tweet for comparison.", author=self.user_profile)
        self.tweet3 = Tweet.objects.create(content="Hello world! This is a test tweet.", author=self.user_profile)  
    def test_tweet_str(self):
        """Test the __str__ method of the Tweet model."""
        self.assertEqual(str(self.tweet1), "Hello world! This is a test tweet.")  

    def test_tweet_repr(self):
        """Test the __repr__ method of the Tweet model."""
        expected_repr = f"<Tweet {self.tweet1.id} by {self.user.username}>"
        self.assertEqual(repr(self.tweet1), expected_repr)

    def test_tweet_eq(self):
        """Test the __eq__ method of the Tweet model for equality and inequality."""
        self.assertTrue(self.tweet1 == self.tweet3)
        self.assertFalse(self.tweet1 == self.tweet2)
        self.assertFalse(self.tweet1 == "Not a tweet object")