from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.common.logging_utils import log_action, serialize_instance
from apps.users.decorators import require_admin, require_permission
from apps.users.forms import (
    LoginForm,
    RolePermissionsForm,
    UserCreateForm,
    UserEditForm,
    UserSearchForm,
    VerifyCodeForm,
)
from apps.users.models import Permission, Role, User
from apps.users.services import (
    authenticate_credentials,
    close_active_sessions,
    complete_admin_login,
    send_employee_verification_code,
    verify_employee_code,
)


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower()
        password = form.cleaned_data['password']
        user = authenticate_credentials(email, password)

        if not user:
            form.add_error(None, 'Email yoki parol noto\'g\'ri')
        elif user.is_admin_user:
            login(request, user)
            complete_admin_login(user, request)
            return redirect('dashboard')
        else:
            send_employee_verification_code(user, request)
            request.session['pending_user_id'] = user.pk
            messages.info(request, 'Tasdiqlash kodi emailga yuborildi.')
            return redirect('verify-code')

    return render(request, 'users/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def verify_code_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        return redirect('login')

    user = get_object_or_404(User, pk=pending_user_id)
    form = VerifyCodeForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['code']
        if verify_employee_code(user, code, request):
            login(request, user)
            request.session.pop('pending_user_id', None)
            return redirect('dashboard')
        form.add_error('code', 'Kod noto\'g\'ri yoki muddati o\'tgan')

    return render(request, 'users/verify_code.html', {'form': form, 'user': user})


@login_required
@require_POST
def logout_view(request):
    close_active_sessions(request.user)
    log_action(
        request=request,
        action='auth.logout',
        model_name='users.User',
        object_id=request.user.pk,
    )
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    return render(request, 'users/dashboard.html')


@require_permission('clients', 'read')
def clients_demo_view(request):
    return render(request, 'users/clients_demo.html')


@require_admin
def admin_user_list(request):
    users = User.objects.filter(is_archived=False).select_related('role')
    search_form = UserSearchForm(request.GET or None)

    if search_form.is_valid():
        q = search_form.cleaned_data.get('q')
        user_type = search_form.cleaned_data.get('user_type')
        role = search_form.cleaned_data.get('role')
        status = search_form.cleaned_data.get('status')

        if q:
            users = users.filter(
                Q(email__icontains=q)
                | Q(full_name__icontains=q)
                | Q(phone__icontains=q)
            )
        if user_type:
            users = users.filter(user_type=user_type)
        if role:
            users = users.filter(role=role)
        if status == 'active':
            users = users.filter(is_active=True, is_blocked=False)
        elif status == 'blocked':
            users = users.filter(is_blocked=True)
        elif status == 'archived':
            users = User.objects.filter(is_archived=True).select_related('role')

    return render(request, 'users/admin/user_list.html', {
        'users': users,
        'search_form': search_form,
    })


@require_admin
@require_http_methods(['GET', 'POST'])
def admin_user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_action(
            request=request,
            action='user.create',
            instance=user,
            new_data=serialize_instance(user),
        )
        messages.success(request, 'Foydalanuvchi yaratildi.')
        return redirect('admin-user-edit', user_id=user.pk)

    return render(request, 'users/admin/user_form.html', {
        'form': form,
        'title': 'Yangi foydalanuvchi',
    })


@require_admin
@require_http_methods(['GET', 'POST'])
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    old_data = serialize_instance(user)
    form = UserEditForm(request.POST or None, instance=user)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_action(
            request=request,
            action='user.update',
            instance=user,
            old_data=old_data,
            new_data=serialize_instance(user),
        )
        messages.success(request, 'Foydalanuvchi yangilandi.')
        return redirect('admin-user-edit', user_id=user.pk)

    active_sessions = user.work_sessions.filter(is_active=True).order_by('-login_at')
    return render(request, 'users/admin/user_edit.html', {
        'form': form,
        'edited_user': user,
        'active_sessions': active_sessions,
        'title': 'Foydalanuvchini tahrirlash',
    })


@require_admin
@require_POST
def admin_user_archive(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_archived=False)
    old_data = serialize_instance(user)
    user.archive()
    close_active_sessions(user, invalidate_sessions=True)
    log_action(
        request=request,
        action='user.archive',
        instance=user,
        old_data=old_data,
        new_data=serialize_instance(user),
    )
    messages.success(request, 'Foydalanuvchi arxivlandi.')
    return redirect('admin-user-list')


@require_admin
@require_POST
def admin_user_block(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    old_data = serialize_instance(user)
    reason = request.POST.get('reason', 'Admin tomonidan bloklandi')
    user.block(reason)
    close_active_sessions(user, invalidate_sessions=True)
    log_action(
        request=request,
        action='user.block',
        instance=user,
        old_data=old_data,
        new_data=serialize_instance(user),
    )
    messages.warning(request, 'Foydalanuvchi bloklandi.')
    return redirect('admin-user-edit', user_id=user.pk)


@require_admin
@require_POST
def admin_user_unblock(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    old_data = serialize_instance(user)
    user.unblock()
    log_action(
        request=request,
        action='user.unblock',
        instance=user,
        old_data=old_data,
        new_data=serialize_instance(user),
    )
    messages.success(request, 'Foydalanuvchi blokdan chiqarildi.')
    return redirect('admin-user-edit', user_id=user.pk)


@require_admin
@require_POST
def admin_force_logout(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    close_active_sessions(user, invalidate_sessions=True)
    log_action(
        request=request,
        action='user.force_logout',
        instance=user,
    )
    messages.success(request, 'Foydalanuvchi sessiyasi yopildi.')
    return redirect('admin-user-edit', user_id=user.pk)


@require_admin
def admin_role_list(request):
    roles = Role.objects.prefetch_related('permissions').all()
    return render(request, 'users/admin/role_list.html', {'roles': roles})


@require_admin
@require_http_methods(['GET', 'POST'])
def admin_role_edit(request, role_id):
    role = get_object_or_404(Role, pk=role_id)
    old_data = {
        'name': role.name,
        'permissions': list(role.permissions.values('module', 'can_read', 'can_write', 'can_delete')),
    }
    form = RolePermissionsForm(request.POST or None, role=role)

    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(
            request=request,
            action='role.update',
            instance=role,
            old_data=old_data,
            new_data={
                'name': role.name,
                'permissions': list(role.permissions.values('module', 'can_read', 'can_write', 'can_delete')),
            },
        )
        messages.success(request, f'"{role.name}" roli yangilandi.')
        return redirect('admin-role-edit', role_id=role.pk)

    permission_rows = [
        {
            'module': module,
            'label': label,
            'read_field': form[f'{module}_read'],
            'write_field': form[f'{module}_write'],
            'delete_field': form[f'{module}_delete'],
        }
        for module, label in Permission.MODULE_CHOICES
    ]
    return render(request, 'users/admin/role_edit.html', {
        'role': role,
        'form': form,
        'permission_rows': permission_rows,
    })
