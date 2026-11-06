from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from apps.accounts.models import CustomerProfile, Address

User = get_user_model()


class AccountsAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_data = {
            'username': 'lord_chiron',
            'first_name': 'Jean',
            'last_name': 'Bugatti',
            'email': 'jean@molsheim-hypercars.fr',
            'password1': 'AureviaSecret2026!#',
            'password2': 'AureviaSecret2026!#'
        }

    def test_customer_registration_success(self):
        url = reverse('accounts:register')
        response = self.client.post(url, data=self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='lord_chiron').exists())

        user = User.objects.get(username='lord_chiron')
        self.assertEqual(user.email, 'jean@molsheim-hypercars.fr')
        self.assertEqual(user.first_name, 'Jean')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, CustomerProfile)

    def test_registration_duplicate_email_rejected(self):
        # Create initial user
        User.objects.create_user(
            username='existing_user',
            email='jean@molsheim-hypercars.fr',
            password='TestPassword123!'
        )
        url = reverse('accounts:register')
        response = self.client.post(url, data=self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'An account with this email address is already registered.')

    def test_registration_password_mismatch_rejected(self):
        bad_data = self.user_data.copy()
        bad_data['password2'] = 'MismatchPassword999!'
        url = reverse('accounts:register')
        response = self.client.post(url, data=bad_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='lord_chiron').exists())

    def test_client_login_and_logout(self):
        user = User.objects.create_user(
            username='collector_one',
            email='collector@aurevia.com',
            password='SecureCollector2026!'
        )
        url_login = reverse('accounts:login')
        response_login = self.client.post(url_login, {
            'username': 'collector_one',
            'password': 'SecureCollector2026!'
        }, follow=True)
        self.assertEqual(response_login.status_code, 200)
        self.assertTrue(response_login.context['user'].is_authenticated)

        # Logout
        url_logout = reverse('accounts:logout')
        response_logout = self.client.get(url_logout, follow=True)
        self.assertEqual(response_logout.status_code, 200)
        self.assertFalse(response_logout.context['user'].is_authenticated)

    def test_login_invalid_credentials_rejected(self):
        url_login = reverse('accounts:login')
        response = self.client.post(url_login, {
            'username': 'nonexistent_client',
            'password': 'WrongPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid credentials')

    def test_login_open_redirect_defense_neutralizes_external_url(self):
        user = User.objects.create_user(
            username='redirect_tester',
            email='tester@aurevia.test',
            password='SecureTester2026!'
        )
        url_login = reverse('accounts:login') + '?next=https://malicious-phishing.test/harvest'
        response = self.client.post(url_login, {
            'username': 'redirect_tester',
            'password': 'SecureTester2026!'
        })
        # Must NOT redirect to external domain; must fall back safely to profile
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('malicious-phishing.test', response.url)
        self.assertEqual(response.url, reverse('accounts:profile'))

    def test_login_open_redirect_defense_neutralizes_schemeless_url(self):
        user = User.objects.create_user(
            username='redirect_tester_2',
            email='tester2@aurevia.test',
            password='SecureTester2026!'
        )
        url_login = reverse('accounts:login') + '?next=//evil.test/payload'
        response = self.client.post(url_login, {
            'username': 'redirect_tester_2',
            'password': 'SecureTester2026!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.test', response.url)
        self.assertEqual(response.url, reverse('accounts:profile'))

    def test_login_safe_internal_redirect_preserved(self):
        user = User.objects.create_user(
            username='redirect_tester_3',
            email='tester3@aurevia.test',
            password='SecureTester2026!'
        )
        safe_target = reverse('orders:order_history')
        url_login = reverse('accounts:login') + f'?next={safe_target}'
        response = self.client.post(url_login, {
            'username': 'redirect_tester_3',
            'password': 'SecureTester2026!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, safe_target)


class AccountsProfileAndAddressTestCase(TestCase):
    def setUp(self):
        self.client_a = Client()
        self.client_b = Client()

        self.user_a = User.objects.create_user(
            username='client_alpha',
            email='alpha@maranello.it',
            password='AlphaPassword123!',
            first_name='Enzo',
            last_name='Ferrari'
        )
        self.user_b = User.objects.create_user(
            username='client_beta',
            email='beta@santagata.it',
            password='BetaPassword123!',
            first_name='Ferruccio',
            last_name='Lamborghini'
        )

        self.client_a.force_login(self.user_a)
        self.client_b.force_login(self.user_b)

    def test_anonymous_user_redirected_from_profile(self):
        anon_client = Client()
        url = reverse('accounts:profile')
        response = anon_client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_view_and_update(self):
        url = reverse('accounts:profile')
        response = self.client_a.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertContains(response, 'Enzo')

        # Update profile
        update_data = {
            'first_name': 'Enzo Anselmo',
            'last_name': 'Ferrari',
            'email': 'enzo.anselmo@maranello.it',
            'phone_number': '+39 0536 949111',
            'preferred_currency': 'EUR',
            'preferred_contact_method': 'secure_portal',
            'collector_preferences': 'V12 Icona series allocations and racing prototypes.'
        }
        post_resp = self.client_a.post(url, data=update_data, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        self.user_a.refresh_from_db()
        self.user_a.profile.refresh_from_db()
        self.assertEqual(self.user_a.first_name, 'Enzo Anselmo')
        self.assertEqual(self.user_a.profile.preferred_currency, 'EUR')
        self.assertEqual(self.user_a.profile.phone_number, '+39 0536 949111')

    def test_address_creation_and_default_resolution(self):
        url = reverse('accounts:address_create')
        addr_1_data = {
            'address_type': Address.TYPE_SHIPPING,
            'full_name': 'Scuderia Ferrari SpA',
            'street_line_1': 'Via Enzo Ferrari 27',
            'city': 'Maranello',
            'state_or_province': 'Modena',
            'postal_code': '41053',
            'country': 'Italy',
            'is_default': True
        }
        resp = self.client_a.post(url, data=addr_1_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.user_a.addresses.count(), 1)
        addr_1 = self.user_a.addresses.first()
        self.assertTrue(addr_1.is_default)

        # Create second default shipping address
        addr_2_data = addr_1_data.copy()
        addr_2_data['street_line_1'] = 'Via Abetone Inferiore 4'
        addr_2_data['is_default'] = True
        self.client_a.post(url, data=addr_2_data, follow=True)

        self.assertEqual(self.user_a.addresses.count(), 2)
        addr_1.refresh_from_db()
        addr_2 = self.user_a.addresses.order_by('-id').first()
        self.assertFalse(addr_1.is_default)
        self.assertTrue(addr_2.is_default)

    def test_cross_user_address_isolation_edit_forbidden(self):
        # User A creates an address
        address_a = Address.objects.create(
            user=self.user_a,
            address_type=Address.TYPE_SHIPPING,
            full_name='Enzo Private Villa',
            street_line_1='Largo Garibaldi 1',
            city='Modena',
            state_or_province='MO',
            postal_code='41121',
            country='Italy'
        )

        # User B attempts to access/edit User A's address
        url_edit = reverse('accounts:address_edit', kwargs={'pk': address_a.pk})
        resp_b_get = self.client_b.get(url_edit)
        self.assertEqual(resp_b_get.status_code, 404)

        resp_b_post = self.client_b.post(url_edit, {
            'address_type': Address.TYPE_SHIPPING,
            'full_name': 'Malicious Hijack',
            'street_line_1': 'Hacked Street',
            'city': 'Rome',
            'state_or_province': 'RM',
            'postal_code': '00100',
            'country': 'Italy'
        })
        self.assertEqual(resp_b_post.status_code, 404)

        # Verify address untouched
        address_a.refresh_from_db()
        self.assertEqual(address_a.full_name, 'Enzo Private Villa')

    def test_cross_user_address_isolation_delete_forbidden(self):
        address_a = Address.objects.create(
            user=self.user_a,
            address_type=Address.TYPE_SHIPPING,
            full_name='Enzo Fiorano Trackside Hangar',
            street_line_1='Fiorano Circuit',
            city='Fiorano Modenese',
            state_or_province='MO',
            postal_code='41042',
            country='Italy'
        )

        # User B attempts to delete User A's address
        url_delete = reverse('accounts:address_delete', kwargs={'pk': address_a.pk})
        resp_b_post = self.client_b.post(url_delete)
        self.assertEqual(resp_b_post.status_code, 404)
        self.assertTrue(Address.objects.filter(pk=address_a.pk).exists())

    def test_admin_registration(self):
        self.assertIn(CustomerProfile, site._registry)
        self.assertIn(Address, site._registry)
