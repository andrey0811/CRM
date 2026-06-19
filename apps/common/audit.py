from apps.common.logging_utils import get_client_ip, log_action, serialize_instance


class AuditLogMixin:
    """Mixin for models that should be audited via ActionLog."""

    audit_action_prefix = None

    def get_audit_action_prefix(self):
        return self.audit_action_prefix or self._meta.model_name


def _action_prefix(instance):
    prefix = getattr(instance, 'audit_action_prefix', None)
    if prefix:
        return prefix
    if hasattr(instance, 'get_audit_action_prefix'):
        return instance.get_audit_action_prefix()
    return instance._meta.model_name


def register_audit_signals(model_class):
    """Register post_save/post_delete signals for automatic audit logging."""

    from django.db.models.signals import post_delete, post_save, pre_save

    _old_instances = {}

    def store_old(sender, instance, **kwargs):
        if instance.pk:
            try:
                old = sender.objects.get(pk=instance.pk)
                _old_instances[instance.pk] = serialize_instance(old)
            except sender.DoesNotExist:
                pass

    def audit_save(sender, instance, created, **kwargs):
        request = getattr(instance, '_audit_request', None)
        user = request.user if request and request.user.is_authenticated else None
        prefix = _action_prefix(instance)
        if created:
            log_action(
                user=user,
                ip_address=get_client_ip(request),
                action=f'{prefix}.create',
                model_name=model_class._meta.label,
                object_id=instance.pk,
                new_value=serialize_instance(instance),
            )
        elif instance.pk in _old_instances:
            log_action(
                user=user,
                ip_address=get_client_ip(request),
                action=f'{prefix}.update',
                model_name=model_class._meta.label,
                object_id=instance.pk,
                old_value=_old_instances.pop(instance.pk),
                new_value=serialize_instance(instance),
            )

    def audit_delete(sender, instance, **kwargs):
        request = getattr(instance, '_audit_request', None)
        user = request.user if request and request.user.is_authenticated else None
        prefix = _action_prefix(instance)
        log_action(
            user=user,
            ip_address=get_client_ip(request),
            action=f'{prefix}.delete',
            model_name=model_class._meta.label,
            object_id=instance.pk,
            old_value=serialize_instance(instance),
        )

    pre_save.connect(store_old, sender=model_class, weak=False)
    post_save.connect(audit_save, sender=model_class, weak=False)
    post_delete.connect(audit_delete, sender=model_class, weak=False)
