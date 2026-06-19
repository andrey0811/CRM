from datetime import timedelta

from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.common.models import ActionLog
from apps.users.models import EmailVerificationCode, Role, User, WorkSession
from apps.users.tasks import check_user_anomaly, close_inactive_sessions


class AdminLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='adminpass123',
            full_name='Admin User',
            user_type=User.UserType.ADMIN,
            is_staff=True,
        )

    def test_admin_login_redirects_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'email': 'admin@test.com',
            'password': 'adminpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(WorkSession.objects.filter(user=self.admin, is_active=True).exists())


class EmployeeLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.get(name='Front')
        self.employee = User.objects.create_user(
            email='employee@test.com',
            password='emplpass123',
            full_name='Employee User',
            user_type=User.UserType.EMPLOYEE,
            role=self.role,
        )

    def test_employee_login_redirects_to_verify_code(self):
        response = self.client.post(reverse('login'), {
            'email': 'employee@test.com',
            'password': 'emplpass123',
        })
        self.assertRedirects(response, reverse('verify-code'))
        self.assertTrue(
            EmailVerificationCode.objects.filter(user=self.employee, is_used=False).exists()
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_valid_code_logs_in_and_creates_work_session(self):
        self.client.post(reverse('login'), {
            'email': 'employee@test.com',
            'password': 'emplpass123',
        })
        code = EmailVerificationCode.objects.filter(user=self.employee).first().code
        response = self.client.post(reverse('verify-code'), {'code': code})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(WorkSession.objects.filter(user=self.employee, is_active=True).exists())

    def test_invalid_code_shows_error(self):
        self.client.post(reverse('login'), {
            'email': 'employee@test.com',
            'password': 'emplpass123',
        })
        response = self.client.post(reverse('verify-code'), {'code': '000000'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kod noto')
        self.assertFalse(self.client.session.get('_auth_user_id'))


class InactivityLogoutTests(TestCase):
    def setUp(self):
        self.role = Role.objects.get(name='Front')
        self.employee = User.objects.create_user(
            email='inactive@test.com',
            password='emplpass123',
            full_name='Inactive User',
            user_type=User.UserType.EMPLOYEE,
            role=self.role,
        )

    def test_session_closed_after_5_hours(self):
        self.employee.last_activity_at = timezone.now() - timedelta(hours=6)
        self.employee.save()
        WorkSession.objects.create(user=self.employee, is_active=True)

        close_inactive_sessions()

        session = WorkSession.objects.filter(user=self.employee).first()
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.logout_at)


class PermissionDecoratorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.get(name='Front')
        self.employee = User.objects.create_user(
            email='perm@test.com',
            password='emplpass123',
            full_name='Perm User',
            user_type=User.UserType.EMPLOYEE,
            role=self.role,
        )
        self.client.login(email='perm@test.com', password='emplpass123')

    def test_user_with_permission_can_access_demo(self):
        response = self.client.get(reverse('demo-clients'))
        self.assertEqual(response.status_code, 200)

    def test_user_without_permission_gets_403(self):
        role = Role.objects.create(name='NoAccess')
        user = User.objects.create_user(
            email='noaccess@test.com',
            password='pass12345',
            full_name='No Access',
            user_type=User.UserType.EMPLOYEE,
            role=role,
        )
        self.client.login(email='noaccess@test.com', password='pass12345')
        response = self.client.get(reverse('demo-clients'))
        self.assertEqual(response.status_code, 403)


class AnomalyDetectionTests(TestCase):
    def setUp(self):
        self.role = Role.objects.get(name='Front')
        self.employee = User.objects.create_user(
            email='anomaly@test.com',
            password='emplpass123',
            full_name='Anomaly User',
            user_type=User.UserType.EMPLOYEE,
            role=self.role,
        )

    def test_user_blocked_on_anomaly(self):
        for i in range(31):
            ActionLog.objects.create(
                user=self.employee,
                action='client.view',
                model_name='clients.Client',
                object_id=str(i),
            )

        check_user_anomaly(self.employee.id)
        self.employee.refresh_from_db()

        self.assertTrue(self.employee.is_blocked)
        self.assertIn('Anomaliya', self.employee.blocked_reason)
        self.assertGreaterEqual(len(mail.outbox), 1)
