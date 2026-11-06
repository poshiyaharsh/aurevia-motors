from django.test import TestCase, Client
from django.urls import reverse


class CoreViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_status_and_content(self):
        url = reverse('core:home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')
        self.assertContains(response, 'Aurevia Motors')
        self.assertContains(response, 'Bugatti')
        self.assertContains(response, 'Lamborghini')

    def test_health_check_html(self):
        url = reverse('core:health')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/health.html')
        self.assertContains(response, 'healthy')

    def test_health_check_json(self):
        url = reverse('core:health')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data.get('status'), 'healthy')
        self.assertEqual(json_data.get('service'), 'Aurevia Motors Platform')
