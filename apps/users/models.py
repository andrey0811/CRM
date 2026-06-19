import random
import string
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.audit import AuditLogMixin
from apps.users.managers import UserManager


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Permission(models.Model):
    MODULE_CHOICES = [
        ('users', 'Users'),
        ('clients', 'Clients'),
        ('catalog', 'Catalog'),
        ('tickets', 'Tickets'),
        ('channels_app', 'Channels'),
        ('scripts', 'Scripts'),
        ('analytics', 'Analytics'),
        ('knowledge', 'Knowledge'),
    ]

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    can_read = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        db_table = 'users_modulepermission'
        unique_together = [('role', 'module')]
        ordering = ['module']

    def __str__(self):
        return f'{self.role.name} — {self.module}'


class User(AuditLogMixin, AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EMPLOYEE = 'employee', 'Employee'

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, default='')
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.EMPLOYEE)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.CharField(max_length=255, blank=True, default='')
    blocked_at = models.DateTimeField(null=True, blank=True)

    last_activity_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    audit_action_prefix = 'user'

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def is_admin_user(self):
        return self.user_type == self.UserType.ADMIN or self.is_superuser

    def block(self, reason=''):
        self.is_blocked = True
        self.blocked_reason = reason[:255]
        self.blocked_at = timezone.now()
        self.save(update_fields=['is_blocked', 'blocked_reason', 'blocked_at', 'updated_at'])

    def unblock(self):
        self.is_blocked = False
        self.blocked_reason = ''
        self.blocked_at = None
        self.save(update_fields=['is_blocked', 'blocked_reason', 'blocked_at', 'updated_at'])

    def archive(self):
        self.is_archived = True
        self.is_active = False
        self.save(update_fields=['is_archived', 'is_active', 'updated_at'])

    def update_activity(self):
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.code}'

    @classmethod
    def generate_code(cls):
        return ''.join(random.choices(string.digits, k=6))

    @classmethod
    def create_for_user(cls, user, lifetime_minutes=5):
        code = cls.generate_code()
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=lifetime_minutes),
        )

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class WorkSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='work_sessions')
    login_at = models.DateTimeField(auto_now_add=True)
    logout_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-login_at']

    def __str__(self):
        return f'{self.user.email} — {self.login_at}'

    def close(self):
        if self.is_active:
            self.is_active = False
            self.logout_at = timezone.now()
            self.save(update_fields=['is_active', 'logout_at'])
