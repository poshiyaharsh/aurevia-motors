from decimal import Decimal
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from apps.catalog.models import Brand, Vehicle
from apps.cart.cart import Cart, MAX_ALLOCATION_PER_VEHICLE
from apps.cart.context_processors import cart_context


class CartServiceAndViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        self.brand = Brand.objects.create(
            name="Bugatti",
            slug="bugatti",
            country="France"
        )
        self.v_available = Vehicle.objects.create(
            brand=self.brand,
            model_name="W16 Mistral",
            slug="w16-mistral",
            year=2024,
            description="Ultimate open-top hypercar.",
            price=Decimal("5000000.00"),
            currency="USD",
            status=Vehicle.STATUS_AVAILABLE
        )
        self.v_reserved = Vehicle.objects.create(
            brand=self.brand,
            model_name="Divo",
            slug="bugatti-divo",
            year=2021,
            description="Coachbuilt track aerodynamics.",
            price=Decimal("5800000.00"),
            currency="USD",
            status=Vehicle.STATUS_RESERVED
        )
        self.v_sold = Vehicle.objects.create(
            brand=self.brand,
            model_name="La Voiture Noire",
            slug="la-voiture-noire",
            year=2019,
            description="Tribute to Type 57 SC Atlantic.",
            price=Decimal("18700000.00"),
            currency="USD",
            status=Vehicle.STATUS_SOLD
        )

    def test_add_available_vehicle_to_cart(self):
        url = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_available.id})
        response = self.client.post(url, {'quantity': 1}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_detail.html')
        self.assertContains(response, "W16 Mistral")
        self.assertContains(response, "5,000,000.00")

    def test_prevent_adding_unavailable_vehicles(self):
        # Reserved vehicle
        url_reserved = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_reserved.id})
        resp_reserved = self.client.post(url_reserved, {'quantity': 1}, follow=True)
        self.assertContains(resp_reserved, "cannot be added to cart")

        # Sold vehicle
        url_sold = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_sold.id})
        resp_sold = self.client.post(url_sold, {'quantity': 1}, follow=True)
        self.assertContains(resp_sold, "cannot be added to cart")

        # Verify cart remains empty
        session = self.client.session
        cart = session.get('aurevia_atelier_cart', {})
        self.assertEqual(len(cart), 0)

    def test_quantity_update_and_clamping(self):
        # Add vehicle
        url_add = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_available.id})
        self.client.post(url_add, {'quantity': 1})

        # Update to 3
        url_update = reverse('cart:cart_update', kwargs={'vehicle_id': self.v_available.id})
        resp_update = self.client.post(url_update, {'quantity': 3}, follow=True)
        self.assertEqual(resp_update.status_code, 200)
        self.assertContains(resp_update, "15,000,000.00")  # 3 * 5,000,000

        # Attempt to exceed maximum allocation (> 5 clamped to 5)
        self.client.post(url_update, {'quantity': 99}, follow=True)
        session = self.client.session
        cart = session.get('aurevia_atelier_cart', {})
        self.assertEqual(cart[str(self.v_available.id)]['quantity'], MAX_ALLOCATION_PER_VEHICLE)

    def test_quantity_zero_or_negative_removes_item(self):
        # Add vehicle
        url_add = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_available.id})
        self.client.post(url_add, {'quantity': 2})

        # Update to 0
        url_update = reverse('cart:cart_update', kwargs={'vehicle_id': self.v_available.id})
        self.client.post(url_update, {'quantity': 0}, follow=True)

        session = self.client.session
        cart = session.get('aurevia_atelier_cart', {})
        self.assertNotIn(str(self.v_available.id), cart)

    def test_remove_item_from_cart(self):
        url_add = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_available.id})
        self.client.post(url_add, {'quantity': 1})

        url_remove = reverse('cart:cart_remove', kwargs={'vehicle_id': self.v_available.id})
        resp_remove = self.client.get(url_remove, follow=True)
        self.assertEqual(resp_remove.status_code, 200)
        self.assertContains(resp_remove, "Your Atelier Cart is Empty")

    def test_clear_cart(self):
        url_add = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_available.id})
        self.client.post(url_add, {'quantity': 1})

        url_clear = reverse('cart:cart_clear')
        resp_clear = self.client.get(url_clear, follow=True)
        self.assertEqual(resp_clear.status_code, 200)
        self.assertContains(resp_clear, "Your atelier cart has been cleared.")

    def test_price_tampering_prevention(self):
        # Malicious client sends a fake price in POST request
        url_add = reverse('cart:cart_add', kwargs={'vehicle_id': self.v_available.id})
        self.client.post(url_add, {
            'quantity': 2,
            'price': '1.00',  # Fake price submitted by attacker
            'total_price': '2.00'
        }, follow=True)

        # Verify server recalculates strictly from DB price ($5,000,000 * 2 = $10,000,000)
        url_detail = reverse('cart:cart_detail')
        response = self.client.get(url_detail)
        self.assertContains(response, "10,000,000.00")
        self.assertNotContains(response, "2.00")

    def test_cart_context_processor(self):
        request = self.factory.get('/')
        request.session = self.client.session
        cart_data = cart_context(request)
        self.assertIn('cart', cart_data)
        self.assertEqual(len(cart_data['cart']), 0)
