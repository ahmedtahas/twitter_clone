from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileViewSet, TweetViewSet, UserRegistrationAPIView, UserProfileAPIView, ActiveUsersAPIView, follow_user, unfollow_user, FeedAPIView, NotificationAPIView, like_tweet, retweet_tweet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'users', UserProfileViewSet)
router.register(r'tweets', TweetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', UserRegistrationAPIView.as_view(), name='auth_register'),
    path('auth/profile/', UserProfileAPIView.as_view(), name='auth_profile'),
    path('active-users/', ActiveUsersAPIView.as_view(), name='active-users'),
    path('follow/<str:username>/', follow_user, name='follow_user'),
    path('unfollow/<str:username>/', unfollow_user, name='unfollow_user'),
    path('feed/', FeedAPIView.as_view(), name='user_feed'),
    path('notifications/', NotificationAPIView.as_view(), name='notifications'),
    path('like/<int:tweet_id>/', like_tweet, name='like_tweet'),
    path('retweet/<int:tweet_id>/', retweet_tweet, name='retweet_tweet'),
]