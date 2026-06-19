from django.db import migrations


MODULES = [
    'users', 'clients', 'catalog', 'tickets',
    'channels_app', 'scripts', 'analytics', 'knowledge',
]

ROLE_PERMISSIONS = {
    'Front': {
        'clients': {'can_read': True, 'can_write': True, 'can_delete': False},
        'tickets': {'can_read': True, 'can_write': True, 'can_delete': False},
        'catalog': {'can_read': True, 'can_write': False, 'can_delete': False},
    },
    'Bek': {
        'catalog': {'can_read': True, 'can_write': True, 'can_delete': False},
        'clients': {'can_read': True, 'can_write': False, 'can_delete': False},
    },
    'Gibrid': {
        'clients': {'can_read': True, 'can_write': True, 'can_delete': False},
        'catalog': {'can_read': True, 'can_write': True, 'can_delete': False},
        'tickets': {'can_read': True, 'can_write': True, 'can_delete': False},
    },
    'Kontent': {
        'catalog': {'can_read': True, 'can_write': True, 'can_delete': False},
    },
    'Lokomotiv': {
        module: {
            'can_read': True,
            'can_write': module == 'tickets',
            'can_delete': False,
        }
        for module in MODULES
    },
}


def seed_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Permission = apps.get_model('users', 'Permission')

    for role_name, perms in ROLE_PERMISSIONS.items():
        role, _ = Role.objects.get_or_create(
            name=role_name,
            defaults={'is_system': True},
        )
        for module, rights in perms.items():
            Permission.objects.get_or_create(
                role=role,
                module=module,
                defaults=rights,
            )


def unseed_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
