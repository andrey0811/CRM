from django.contrib import admin

from apps.users.models import EmailVerificationCode, Permission, Role, User, WorkSession


class PermissionInline(admin.TabularInline):
    model = Permission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_system')
    search_fields = ('name',)
    inlines = [PermissionInline]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'full_name', 'user_type', 'role', 'is_active',
        'is_blocked', 'is_archived', 'created_at',
    )
    list_filter = ('user_type', 'is_active', 'is_blocked', 'is_archived', 'role')
    search_fields = ('email', 'full_name', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'last_activity_at', 'blocked_at')
    fieldsets = (
        (None, {'fields': ('email', 'full_name', 'phone', 'password')}),
        ('Role & Type', {'fields': ('user_type', 'role',)}),
        ('Status', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'is_archived',
            'is_blocked', 'blocked_reason', 'blocked_at',
        )}),
        ('Activity', {'fields': ('last_activity_at', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if 'password' in form.changed_data and form.cleaned_data.get('password'):
            obj.set_password(form.cleaned_data['password'])
        elif not change:
            obj.set_password(form.cleaned_data.get('password', 'changeme'))
        super().save_model(request, obj, form, change)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'module', 'can_read', 'can_write', 'can_delete')
    list_filter = ('module', 'role')


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used',)
    readonly_fields = ('created_at',)


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_at', 'logout_at', 'ip_address', 'is_active')
    list_filter = ('is_active',)
    readonly_fields = ('login_at',)
