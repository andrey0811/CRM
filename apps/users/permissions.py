def user_has_module_permission(user, module, action='read'):
    if not user or not user.is_authenticated:
        return False
    if user.is_admin_user:
        return True
    if user.is_blocked or user.is_archived:
        return False
    if not user.role_id:
        return False

    perm = user.role.permissions.filter(module=module).first()
    if not perm:
        return False

    if action == 'read':
        return perm.can_read
    if action == 'write':
        return perm.can_write
    if action == 'delete':
        return perm.can_delete
    return False
