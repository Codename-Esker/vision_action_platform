from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AccountFlowTests(TestCase):
    def test_analysis_page_requires_login(self):
        page = reverse("analyses:index")
        response = self.client.get(page)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={page}")

    def test_signup_login_and_logout(self):
        username = "vision_test"
        password = "Vision-Test-Pass-827!"

        response = self.client.post(
            reverse("accounts:signup"),
            {"username": username, "password1": password, "password2": password},
        )
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertTrue(get_user_model().objects.filter(username=username).exists())

        response = self.client.post(
            reverse("accounts:login"),
            {"username": username, "password": password},
            follow=True,
        )
        self.assertRedirects(response, reverse("analyses:index"))
        self.assertContains(response, f"{username}님으로 로그인했습니다.")

        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
