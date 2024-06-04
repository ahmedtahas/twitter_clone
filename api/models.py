from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        app_label = 'api'


class Hashtag(models.Model):
    tag = models.CharField(max_length=100, unique=True)


class Tweet(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    delete_reason = models.CharField(max_length=255, blank=True)
    hashtags = models.ManyToManyField(Hashtag, related_name='tweets')
    parent_tweet = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    def delete(self, *args, **kwargs):
        for reply in self.replies.all():
            reply.delete()
        super().delete(*args, **kwargs)
    def mark_as_deleted(self, delete_reason='No reason provided'):
        self.is_deleted = True
        self.delete_reason = delete_reason if delete_reason else 'No reason provided'
        self.save()
        for reply in self.replies.all():
            reply.mark_as_deleted(delete_reason='Parent tweet deleted')
    def __str__(self):
        return f"{self.content[:140]}"

    def __repr__(self):
        return f"<Tweet {self.id} by {self.author.user.username}>"

    def __eq__(self, other):
        if isinstance(other, Tweet):
            return self.content == other.content and self.author == other.author
        return False
            
class Follow(models.Model):
    follower = models.ForeignKey(UserProfile, related_name="following", on_delete=models.CASCADE)
    followed = models.ForeignKey(UserProfile, related_name="followers", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')  

    def __str__(self):
        return f"{self.follower.user.username} follows {self.followed.user.username}"

class Notification(models.Model):
    recipient = models.ForeignKey(UserProfile, related_name='notifications', on_delete=models.CASCADE)
    sender = models.ForeignKey(UserProfile, related_name='sent_notifications', on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.user.username}: {self.message}"

class Like(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tweet') 

class Retweet(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='retweets')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tweet') 