from django.core.management.base import BaseCommand

from apps.users.models import Role, User


class Command(BaseCommand):
    help = 'Test login uchun namuna admin va xodim yaratadi'

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'full_name': 'Test Admin',
                'user_type': User.UserType.ADMIN,
                'is_staff': True,
            },
        )
        if created or options['reset_password']:
            admin.set_password('adminpass123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Admin: admin@test.com / adminpass123'))

        front_role = Role.objects.filter(name='Front').first()
        employee, created = User.objects.get_or_create(
            email='employee@test.com',
            defaults={
                'full_name': 'Test Employee',
                'user_type': User.UserType.EMPLOYEE,
                'role': front_role,
            },
        )
        if created or options['reset_password']:
            employee.set_password('emplpass123')
            employee.save()
            self.stdout.write(self.style.SUCCESS('Xodim: employee@test.com / emplpass123'))

        if not created and not options['reset_password']:
            self.stdout.write('Foydalanuvchilar allaqachon mavjud. Parolni yangilash uchun --reset-password')

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-password',
            action='store_true',
            help='Mavjud foydalanuvchi parollarini qayta o\'rnatish',
        )
