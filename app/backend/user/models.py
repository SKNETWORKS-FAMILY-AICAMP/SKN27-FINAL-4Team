from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    CHARACTER_CHOICES = [
        ('haeon', '해온이'),
        ('greung', '그릉이'),
        ('dalkong', '달콩이'),
    ]

    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=30)
    character = models.CharField(max_length=10, choices=CHARACTER_CHOICES, blank=True)
    onboarding_done = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname']

    class Meta:
        db_table = 'users'


class OAuthAccount(models.Model):
    PROVIDER_CHOICES = [
        ('kakao', 'Kakao'),
        ('naver', 'Naver'),
        ('google', 'Google'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='oauth_accounts',
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=191)
    email = models.EmailField(blank=True)
    raw_profile = models.JSONField(default=dict, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oauth_accounts'
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_user_id'],
                name='uniq_oauth_provider_user',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'provider'], name='oauth_user_provider_idx'),
            models.Index(fields=['provider', 'email'], name='oauth_provider_email_idx'),
        ]

    def __str__(self):
        return f'{self.provider}:{self.provider_user_id}'


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    job = models.CharField(max_length=100, blank=True)
    hobbies = models.JSONField(default=list, blank=True)
    interests = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f'{self.user_id} profile'


class UserPreferenceKeyword(models.Model):
    KEYWORD_TYPE_CHOICES = [
        ('hobby', '취미'),
        ('interest', '관심분야'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='preference_keywords',
    )
    keyword_type = models.CharField(max_length=20, choices=KEYWORD_TYPE_CHOICES)
    label = models.CharField(max_length=100)
    source = models.CharField(max_length=30, default='onboarding')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_preference_keywords'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'keyword_type', 'label'],
                name='uniq_user_preference_keyword',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'keyword_type'], name='user_pref_keyword_user_idx'),
            models.Index(fields=['keyword_type', 'label'], name='user_pref_keyword_label_idx'),
        ]

    def __str__(self):
        return f'{self.user_id} {self.keyword_type} {self.label}'
