from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from .models import UserProfile, Tweet, Hashtag, Follow, Notification, Like, Retweet
from .serializers import UserProfileSerializer, TweetSerializer, NotificationSerializer
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404


@api_view(['POST'])
def follow_user(request, username):
    user_to_follow = get_object_or_404(UserProfile, user__username=username)
    if Follow.objects.filter(follower=request.user.userprofile, followed=user_to_follow).exists():
        return Response({'error': 'You are already following this user'}, status=status.HTTP_400_BAD_REQUEST)
    Follow.objects.create(follower=request.user.userprofile, followed=user_to_follow)
    Notification.objects.create(
        recipient=user_to_follow,
        sender=request.user.userprofile,
        message=f"{request.user.username} has started following you."
    )
    return Response({'message': 'User followed successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def unfollow_user(request, username):
    user_to_unfollow = get_object_or_404(UserProfile, user__username=username)
    follow_relation = Follow.objects.filter(follower=request.user.userprofile, followed=user_to_unfollow)
    if not follow_relation.exists():
        return Response({'error': 'You are not following this user'}, status=status.HTTP_400_BAD_REQUEST)
    follow_relation.delete()
    return Response({'message': 'User unfollowed successfully'}, status=status.HTTP_204_NO_CONTENT)


class FeedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        following_users = Follow.objects.filter(follower=request.user.userprofile).values_list('followed_id', flat=True)
        
        tweets = Tweet.objects.filter(author_id__in=following_users, is_deleted=False).order_by('-created_at')
        
        serializer = TweetSerializer(tweets, many=True)
        return Response(serializer.data)

class ActiveUsersAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(last_login__isnull=False).order_by('-last_login')[:10]
        data = [{'username': user.username, 'last_login': user.last_login} for user in users]
        return Response(data)
    

def calculate_deletion_statistics(start_date, end_date):
    deleted_tweets = Tweet.objects.filter(
        is_deleted=True,
        created_at__range=[start_date, end_date]
    )

    deletion_reasons_count = deleted_tweets.values('delete_reason').annotate(
        count=Count('delete_reason')
    ).order_by('-count')

    deletion_statistics = {item['delete_reason']: item['count'] for item in deletion_reasons_count}

    return deletion_statistics


class UserProfileAPIView(APIView):
       def get(self, request):
           user_profile = {
               'username': request.user.username,
               'bio': request.user.userprofile.bio
           }
           return Response(user_profile)


class UserRegistrationAPIView(APIView):
       permission_classes = [AllowAny]

       def post(self, request):
           username = request.data.get('username')
           password = request.data.get('password')
           if not username or not password:
               return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
           user = User.objects.create_user(username=username, password=password)
           return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class TweetViewSet(viewsets.ModelViewSet):
    queryset = Tweet.objects.all()
    serializer_class = TweetSerializer
    permission_classes = [IsAuthenticated]
    @action(detail=False, methods=['get'])
    def popular_hashtags(self, request):
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_tweets = self.queryset.filter(created_at__gte=seven_days_ago)
        hashtag_counts = Hashtag.objects.filter(tweets__in=recent_tweets)\
                                        .annotate(num_tweets=Count('tweets'))\
                                        .order_by('-num_tweets')
        data = [{'hashtag': hashtag.tag, 'count': hashtag.num_tweets} for hashtag in hashtag_counts]
        return Response(data)

    def destroy(self, request, *args, **kwargs):
        tweet = self.get_object()
        if tweet.is_deleted:
            return Response({'error': 'Tweet is already deleted.'}, status=status.HTTP_400_BAD_REQUEST)

        delete_reason = request.data.get('delete_reason', 'No reason provided')
        if not delete_reason:
            return Response({'error': 'A delete reason must be provided.'}, status=status.HTTP_400_BAD_REQUEST)

        tweet.mark_as_deleted(delete_reason)
        return Response({'status': 'Tweet and its replies marked as deleted'}, status=status.HTTP_204_NO_CONTENT)

class NotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user.userprofile).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def like_tweet(request, tweet_id):
    tweet = get_object_or_404(Tweet, id=tweet_id)
    if Like.objects.filter(user=request.user.userprofile, tweet=tweet).exists():
        return Response({'error': 'You have already liked this tweet'}, status=status.HTTP_400_BAD_REQUEST)
    Like.objects.create(user=request.user.userprofile, tweet=tweet)
    return Response({'message': 'Tweet liked successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def retweet_tweet(request, tweet_id):
    tweet = get_object_or_404(Tweet, id=tweet_id)
    if Retweet.objects.filter(user=request.user.userprofile, tweet=tweet).exists():
        return Response({'error': 'You have already retweeted this tweet'}, status=status.HTTP_400_BAD_REQUEST)
    Retweet.objects.create(user=request.user.userprofile, tweet=tweet)
    return Response({'message': 'Tweet retweeted successfully'}, status=status.HTTP_201_CREATED)
