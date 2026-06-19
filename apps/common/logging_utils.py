from django.forms.models import model_to_dict

from apps.common.models import ActionLog


def get_client_ip(request):
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(
    *,
    user=None,
    request=None,
    ip_address=None,
    action,
    model_name=None,
    instance=None,
    object_id=None,
    old_value=None,
    new_value=None,
    old_data=None,
    new_data=None,
):
    if request is not None:
        if user is None and request.user.is_authenticated:
            user = request.user
        if ip_address is None:
            ip_address = get_client_ip(request)

    if instance is not None:
        model_name = model_name or instance._meta.label
        if object_id is None:
            object_id = instance.pk

    if old_data is not None:
        old_value = old_data
    if new_data is not None:
        new_value = new_data

    return ActionLog.objects.create(
        user=user,
        ip_address=ip_address,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else '',
        old_value=old_value,
        new_value=new_value,
    )


def serialize_instance(instance, exclude=None):
    if instance is None:
        return None
    exclude = exclude or ['password']
    data = model_to_dict(instance)
    for field in exclude:
        data.pop(field, None)
    for key, value in list(data.items()):
        if hasattr(value, 'isoformat'):
            data[key] = value.isoformat()
        elif hasattr(value, 'pk'):
            data[key] = value.pk
    return data
