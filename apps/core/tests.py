import json
import sqlite3
import tempfile
from pathlib import Path
from io import StringIO
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.core.management import call_command
from apps.core.views import custom_404_view, custom_500_view


class CoreViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        call_command('seed_marques', stdout=StringIO())

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

    def test_custom_404_view_html(self):
        request = self.factory.get('/nonexistent-supercar-route/')
        response = custom_404_view(request)
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Destination Unknown', response.content)

    def test_custom_404_view_json(self):
        request = self.factory.get('/nonexistent-supercar-route/', HTTP_ACCEPT='application/json')
        response = custom_404_view(request)
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('status_code'), 404)

    def test_custom_500_view_html(self):
        request = self.factory.get('/trigger-server-error/')
        response = custom_500_view(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b'Technical Interruption', response.content)

    def test_custom_500_view_json(self):
        request = self.factory.get('/trigger-server-error/', HTTP_ACCEPT='application/json')
        response = custom_500_view(request)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('status_code'), 500)

    def test_backup_db_command(self):
        out = StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            fake_db = temp_dir_path / 'sample.sqlite3'
            # Initialize a real sqlite db
            conn = sqlite3.connect(str(fake_db))
            conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);")
            conn.commit()
            conn.close()

            dest_backup = temp_dir_path / 'backups'
            call_command('backup_db', src=str(fake_db), dest=str(dest_backup), stdout=out)
            output = out.getvalue()
            self.assertIn('Successfully created backup', output)
            self.assertTrue(any(dest_backup.glob('db_backup_*.sqlite3')))
