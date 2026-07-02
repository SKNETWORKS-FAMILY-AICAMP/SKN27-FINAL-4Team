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
        ('pori',  '포리'),   # 레서판다 / 밝음·응원형
        ('kkami', '까미'),   # 고양이 / 깊음·묵직형
        ('toto',  '토토'),   # 수달 / 장난·환기형
        ('yeoul', '여울'),   # 뱁새 / 차분·포근형
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
