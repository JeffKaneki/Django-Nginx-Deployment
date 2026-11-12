from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.recaptcha import verify_recaptcha
from unittest.mock import patch

User = get_user_model()


class AccountWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", email="admin@example.com", password="Safe-pass-456",
            role=User.Role.ADMIN,
        )
        self.superadmin = User.objects.create_user(
            username="root1", email="root@example.com", password="Safe-pass-456",
            role=User.Role.SUPERADMIN,
        )
        self.regular = User.objects.create_user(
            username="member1", email="member@example.com", password="Safe-pass-456",
        )

    @patch("accounts.forms.verify_recaptcha", return_value=True)
    def test_registration_login_and_logout(self, verify_captcha):
        response = self.client.post(reverse("register"), {
            "username": "newmember",
            "email": "new@example.com",
            "phone": "555-0101",
            "address": "1 Main Street",
            "password1": "A-strong-password-77",
            "password2": "A-strong-password-77",
        })
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="newmember")
        self.assertEqual(user.role, User.Role.USER)
        self.assertNotEqual(user.password, "A-strong-password-77")
        self.assertTrue(user.check_password("A-strong-password-77"))

        response = self.client.post(reverse("login"), {
            "username": "newmember", "password": "A-strong-password-77",
        })
        self.assertRedirects(response, reverse("dashboard"))
        verify_captcha.assert_called_once()
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch("accounts.forms.verify_recaptcha", return_value=False)
    def test_login_requires_successful_captcha(self, verify_captcha):
        response = self.client.post(reverse("login"), {
            "username": "member1",
            "password": "Safe-pass-456",
            "g-recaptcha-response": "invalid-token",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Complete the I'm not a robot CAPTCHA verification and try again.",
            response.context["form"].non_field_errors(),
        )
        verify_captcha.assert_called_once()
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_form_displays_captcha_widget(self):
        with self.settings(RECAPTCHA_SITE_KEY="public-test-site-key"):
            response = self.client.get(reverse("login"))
        self.assertContains(response, 'class="g-recaptcha"')
        self.assertContains(response, 'data-sitekey="public-test-site-key"')

    @patch("accounts.recaptcha.urlopen")
    def test_recaptcha_verification_posts_secret_and_token(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"success": true}'
        with self.settings(
            RECAPTCHA_SITE_KEY="site-key",
            RECAPTCHA_SECRET_KEY="secret-key",
        ):
            self.assertTrue(verify_recaptcha("captcha-token", "203.0.113.8"))

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://www.google.com/recaptcha/api/siteverify")
        self.assertIn(b"secret=secret-key", request.data)
        self.assertIn(b"response=captcha-token", request.data)
        self.assertIn(b"remoteip=203.0.113.8", request.data)

    @patch("accounts.recaptcha.urlopen", side_effect=OSError("verification offline"))
    def test_recaptcha_fails_closed_when_verification_service_is_unavailable(self, urlopen):
        with self.settings(
            RECAPTCHA_SITE_KEY="site-key",
            RECAPTCHA_SECRET_KEY="secret-key",
        ):
            self.assertFalse(verify_recaptcha("captcha-token"))

    @patch("accounts.recaptcha.urlopen")
    def test_recaptcha_fails_closed_when_keys_are_missing(self, urlopen):
        with self.settings(RECAPTCHA_SITE_KEY="", RECAPTCHA_SECRET_KEY=""):
            self.assertFalse(verify_recaptcha("captcha-token"))
        urlopen.assert_not_called()

    def test_admin_can_create_and_edit_teacher(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts")).status_code, 200)
        self.assertEqual(self.client.get(reverse("teachers")).status_code, 200)
        response = self.client.post(reverse("teachers"), {
            "username": "teacher1", "email": "teacher@example.com",
            "phone": "555-0202", "address": "2 School Lane",
            "password": "Teacher-pass-456",
        })
        self.assertRedirects(response, reverse("teachers"))
        teacher = User.objects.get(username="teacher1")
        self.assertEqual(teacher.role, User.Role.TEACHER)
        self.assertTrue(teacher.check_password("Teacher-pass-456"))
        self.assertEqual(self.client.get(reverse("teacher_edit", args=[teacher.pk])).status_code, 200)

        response = self.client.post(reverse("teacher_edit", args=[teacher.pk]), {
            "username": "teacher1", "email": "teacher@example.com",
            "phone": "555-0203", "address": "3 School Lane", "password": "",
        })
        self.assertRedirects(response, reverse("teachers"))
        teacher.refresh_from_db()
        self.assertEqual(teacher.phone, "555-0203")
        self.assertTrue(teacher.check_password("Teacher-pass-456"))

    def test_admin_role_permissions_and_superadmin_password_reset(self):
        self.client.force_login(self.regular)
        self.assertRedirects(self.client.get(reverse("accounts")), reverse("dashboard"))
        self.client.force_login(self.admin)
        response = self.client.post(reverse("set_role", args=[self.regular.pk]), {
            "role": User.Role.SUPERADMIN,
        })
        self.assertRedirects(response, reverse("accounts"))
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, User.Role.USER)

        self.client.force_login(self.superadmin)
        self.assertEqual(self.client.get(reverse("account_password", args=[self.regular.pk])).status_code, 200)
        response = self.client.post(reverse("set_role", args=[self.regular.pk]), {
            "role": User.Role.MANAGER,
        })
        self.assertRedirects(response, reverse("accounts"))
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, User.Role.MANAGER)

        response = self.client.post(reverse("account_password", args=[self.regular.pk]), {
            "new_password1": "Changed-pass-987",
            "new_password2": "Changed-pass-987",
        })
        self.assertRedirects(response, reverse("accounts"))
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password("Changed-pass-987"))

    def test_regular_user_can_change_own_password(self):
        self.client.force_login(self.regular)
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)
        response = self.client.post(reverse("password_change"), {
            "old_password": "Safe-pass-456",
            "new_password1": "Updated-pass-654",
            "new_password2": "Updated-pass-654",
        })
        self.assertRedirects(response, reverse("password_change"))
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password("Updated-pass-654"))

    def test_login_and_admin_routes_require_authentication_and_csrf(self):
        self.assertRedirects(self.client.get(reverse("dashboard")), f"{reverse('login')}?next={reverse('dashboard')}")
        from django.test import Client

        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post(reverse("login"), {}).status_code, 403)
        self.assertEqual(csrf_client.post(reverse("logout")).status_code, 403)

    def test_createsuperuser_gets_superadmin_role_and_access(self):
        superuser = User.objects.create_superuser(
            username="siteadmin", email="siteadmin@example.com", password="Safe-pass-456",
        )
        self.assertEqual(superuser.role, User.Role.SUPERADMIN)
        self.assertTrue(superuser.is_staff)
        self.client.force_login(superuser)
        self.assertEqual(self.client.get(reverse("accounts")).status_code, 200)
        self.assertEqual(self.client.get(reverse("teachers")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_static_and_media_settings(self):
        from django.conf import settings

        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertEqual(settings.STATIC_ROOT.name, "staticfiles")
        self.assertEqual(settings.MEDIA_URL, "/media/")
        self.assertEqual(settings.MEDIA_ROOT.name, "media")
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post(reverse("logout")).status_code, 403)
