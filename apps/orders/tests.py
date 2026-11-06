import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from apps.catalog.models import Brand, Vehicle
from apps.accounts.models import Address
from apps.orders.models import Coupon, Order, OrderItem, Payment
from apps.orders.pricing import PricingEngine, OrderCalculationResult
from apps.orders.payments import PaymentVerificationService
from apps.cart.cart import Cart


class CouponModelTests(TestCase):
    """
    Test suite for Coupon model integrity, normalization, and validations.
    """

    def setUp(self):
        self.now = timezone.now()

    def test_coupon_creation_and_auto_uppercase_code(self):
        coupon = Coupon.objects.create(
            code="  testcode10  ",
            description="10% Privilege Allocation",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('10.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        self.assertEqual(coupon.code, "TESTCODE10")
        self.assertEqual(str(coupon), "TESTCODE10 (10.00% OFF)")

    def test_coupon_clean_valid_to_before_valid_from_raises_error(self):
        coupon = Coupon(
            code="INVALIDDATES",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('10.00'),
            valid_from=self.now,
            valid_to=self.now - timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as ctx:
            coupon.clean()
        self.assertIn('valid_to', ctx.exception.message_dict)

    def test_coupon_clean_percentage_over_100_raises_error(self):
        coupon = Coupon(
            code="OVER100",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('105.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        with self.assertRaises(ValidationError) as ctx:
            coupon.clean()
        self.assertIn('discount_value', ctx.exception.message_dict)

    def test_coupon_clean_percentage_zero_or_negative_raises_error(self):
        coupon = Coupon(
            code="ZEROORNEG",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('0.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        with self.assertRaises(ValidationError) as ctx:
            coupon.clean()
        self.assertIn('discount_value', ctx.exception.message_dict)

    def test_coupon_clean_fixed_zero_or_negative_raises_error(self):
        coupon = Coupon(
            code="FIXEDZERO",
            discount_type=Coupon.DISCOUNT_FIXED,
            discount_value=Decimal('-500.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        with self.assertRaises(ValidationError) as ctx:
            coupon.clean()
        self.assertIn('discount_value', ctx.exception.message_dict)

    def test_coupon_fixed_str_representation(self):
        coupon = Coupon.objects.create(
            code="VIP50K",
            discount_type=Coupon.DISCOUNT_FIXED,
            discount_value=Decimal('50000.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        self.assertEqual(str(coupon), "VIP50K ($50,000.00 OFF)")


class CouponEligibilityTests(TestCase):
    """
    Test suite for coupon business rules, dates, status, and usage restrictions.
    """

    def setUp(self):
        self.now = timezone.now()
        self.active_coupon = Coupon.objects.create(
            code="ACTIVEVIP",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('10.00'),
            min_order_value=Decimal('500000.00'),
            valid_from=self.now - timedelta(days=2),
            valid_to=self.now + timedelta(days=10),
            max_uses=10,
            used_count=0,
            is_active=True,
        )

    def test_can_apply_valid_active_coupon(self):
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('600000.00'))
        self.assertTrue(is_valid)
        self.assertEqual(reason, "Coupon is valid.")

    def test_can_apply_inactive_coupon_rejected(self):
        self.active_coupon.is_active = False
        self.active_coupon.save()
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('600000.00'))
        self.assertFalse(is_valid)
        self.assertIn("inactive", reason.lower())

    def test_can_apply_future_coupon_rejected(self):
        self.active_coupon.valid_from = self.now + timedelta(days=5)
        self.active_coupon.valid_to = self.now + timedelta(days=15)
        self.active_coupon.save()
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('600000.00'))
        self.assertFalse(is_valid)
        self.assertIn("not yet active", reason.lower())

    def test_can_apply_expired_coupon_rejected(self):
        self.active_coupon.valid_from = self.now - timedelta(days=20)
        self.active_coupon.valid_to = self.now - timedelta(days=1)
        self.active_coupon.save()
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('600000.00'))
        self.assertFalse(is_valid)
        self.assertIn("expired", reason.lower())

    def test_can_apply_exhausted_coupon_rejected(self):
        self.active_coupon.used_count = 10
        self.active_coupon.max_uses = 10
        self.active_coupon.save()
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('600000.00'))
        self.assertFalse(is_valid)
        self.assertIn("maximum redemption limit", reason.lower())

    def test_can_apply_subtotal_below_minimum_rejected(self):
        # min_order_value is $500,000. Subtotal is $499,999.99
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('499999.99'))
        self.assertFalse(is_valid)
        self.assertIn("minimum order valuation", reason.lower())

    def test_can_apply_subtotal_equal_or_above_minimum(self):
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('500000.00'))
        self.assertTrue(is_valid)

    def test_can_apply_empty_or_zero_subtotal_rejected(self):
        is_valid, reason = self.active_coupon.can_apply(subtotal=Decimal('0.00'))
        self.assertFalse(is_valid)
        self.assertIn("empty or zero-value", reason.lower())


class PricingEngineCalculationTests(TestCase):
    """
    Test suite for Decimal-safe monetary arithmetic, rounding, tax, and tamper-resistance.
    """

    def setUp(self):
        self.now = timezone.now()
        self.pct_coupon = Coupon.objects.create(
            code="PERCENT10",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('10.00'),
            min_order_value=Decimal('100000.00'),
            max_discount_amount=Decimal('150000.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
            is_active=True,
        )
        self.fixed_coupon = Coupon.objects.create(
            code="FIXED50K",
            discount_type=Coupon.DISCOUNT_FIXED,
            discount_value=Decimal('50000.00'),
            min_order_value=Decimal('100000.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
            is_active=True,
        )

    def test_percentage_discount_calculation(self):
        subtotal = Decimal('1000000.00')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="PERCENT10")
        self.assertTrue(result.is_coupon_applied)
        # 10% of 1,000,000 = 100,000.00 (under 150,000 cap)
        self.assertEqual(result.discount_amount, Decimal('100000.00'))
        self.assertEqual(result.grand_total, Decimal('900000.00'))

    def test_percentage_discount_with_max_cap(self):
        # 10% of 2,500,000 = 250,000 -> capped at 150,000
        subtotal = Decimal('2500000.00')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="PERCENT10")
        self.assertTrue(result.is_coupon_applied)
        self.assertEqual(result.discount_amount, Decimal('150000.00'))
        self.assertEqual(result.grand_total, Decimal('2350000.00'))

    def test_fixed_discount_calculation(self):
        subtotal = Decimal('800000.00')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="FIXED50K")
        self.assertTrue(result.is_coupon_applied)
        self.assertEqual(result.discount_amount, Decimal('50000.00'))
        self.assertEqual(result.grand_total, Decimal('750000.00'))

    def test_discount_exceeding_subtotal_is_capped_at_subtotal_no_negative_total(self):
        # Create a massive coupon
        huge_coupon = Coupon.objects.create(
            code="HUGE500K",
            discount_type=Coupon.DISCOUNT_FIXED,
            discount_value=Decimal('500000.00'),
            min_order_value=Decimal('0.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
            is_active=True,
        )
        subtotal = Decimal('200000.00')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="HUGE500K")
        self.assertTrue(result.is_coupon_applied)
        # Discount cannot exceed subtotal
        self.assertEqual(result.discount_amount, Decimal('200000.00'))
        self.assertEqual(result.grand_total, Decimal('0.00'))

    def test_decimal_rounding_round_half_up(self):
        # Test odd subtotal and percentage: 12.5% of $357,999.55
        # 357999.55 * 0.125 = 44749.94375 -> rounds to 44749.94
        odd_coupon = Coupon.objects.create(
            code="ODD125",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('12.50'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
            is_active=True,
        )
        subtotal = Decimal('357999.55')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="ODD125")
        self.assertEqual(result.discount_amount, Decimal('44749.94'))
        self.assertEqual(result.grand_total, Decimal('313249.61'))

        # Another case where half rounds up: 7.5% of $105.10 = 7.8825 -> 7.88
        # 15.0% of $105.10 = 15.765 -> 15.77 (half up)
        half_up_coupon = Coupon.objects.create(
            code="HALFUP15",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('15.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
            is_active=True,
        )
        result_half = PricingEngine.calculate(subtotal=Decimal('105.10'), coupon_code="HALFUP15")
        self.assertEqual(result_half.discount_amount, Decimal('15.77'))

    def test_nonexistent_coupon_code_rejected(self):
        result = PricingEngine.calculate(subtotal=Decimal('500000.00'), coupon_code="DOESNOTEXIST")
        self.assertFalse(result.is_coupon_applied)
        self.assertEqual(result.discount_amount, Decimal('0.00'))
        self.assertIn("does not exist", result.coupon_rejection_reason)

    def test_case_insensitive_coupon_code(self):
        result = PricingEngine.calculate(subtotal=Decimal('1000000.00'), coupon_code="  percent10  ")
        self.assertTrue(result.is_coupon_applied)
        self.assertEqual(result.coupon.code, "PERCENT10")

    @override_settings(ORDER_TAX_RATE=Decimal('0.08'))
    def test_tax_calculation_applied_to_net_subtotal(self):
        # Subtotal: $1,000,000. Discount: $100,000. Taxable: $900,000.
        # Tax at 8%: $900,000 * 0.08 = $72,000.00.
        # Grand total: $972,000.00
        subtotal = Decimal('1000000.00')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="PERCENT10")
        self.assertEqual(result.tax_amount, Decimal('72000.00'))
        self.assertEqual(result.grand_total, Decimal('972000.00'))

    @override_settings(ORDER_DELIVERY_FEE=Decimal('5000.00'))
    def test_delivery_fee_added_to_grand_total(self):
        subtotal = Decimal('800000.00')
        result = PricingEngine.calculate(subtotal=subtotal, coupon_code="FIXED50K")
        self.assertEqual(result.delivery_fee, Decimal('5000.00'))
        self.assertEqual(result.grand_total, Decimal('755000.00'))


class CartCouponViewIntegrationTests(TestCase):
    """
    Test suite for cart integration, coupon application views, session management, and UI rendering.
    """

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        self.brand = Brand.objects.create(name="Bugatti", slug="bugatti", country="France")
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model_name="Chiron Pur Sport",
            slug="chiron-pur-sport",
            year=2024,
            price=Decimal('3800000.00'),
            currency='USD',
            status=Vehicle.STATUS_AVAILABLE,
        )
        self.coupon = Coupon.objects.create(
            code="FIRST50",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('5.00'),
            min_order_value=Decimal('100000.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=365),
            is_active=True,
        )
        self.min_order_coupon = Coupon.objects.create(
            code="HIGHMIN",
            discount_type=Coupon.DISCOUNT_FIXED,
            discount_value=Decimal('100000.00'),
            min_order_value=Decimal('5000000.00'),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=365),
            is_active=True,
        )

    def test_apply_coupon_valid_workflow(self):
        # 1. Add vehicle to cart
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})

        # 2. Apply coupon
        response = self.client.post(
            reverse('cart:coupon_apply'),
            {'code': 'FIRST50'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FIRST50")
        self.assertContains(response, "Voucher &#x27;FIRST50&#x27; applied")

        # 3. Check session
        session = self.client.session
        self.assertEqual(session.get('aurevia_applied_coupon'), 'FIRST50')

        # 4. Check breakdown in context
        calculation = response.context['calculation']
        self.assertTrue(calculation.is_coupon_applied)
        self.assertEqual(calculation.subtotal, Decimal('3800000.00'))
        # 5% of 3,800,000 = 190,000
        self.assertEqual(calculation.discount_amount, Decimal('190000.00'))
        self.assertEqual(calculation.grand_total, Decimal('3610000.00'))

    def test_apply_coupon_invalid_code(self):
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})
        response = self.client.post(
            reverse('cart:coupon_apply'),
            {'code': 'FAKEXYZ'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not exist")
        session = self.client.session
        self.assertIsNone(session.get('aurevia_applied_coupon'))

    def test_apply_coupon_empty_cart(self):
        # Attempt to apply coupon with nothing in cart
        response = self.client.post(
            reverse('cart:coupon_apply'),
            {'code': 'FIRST50'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot apply a voucher to an empty atelier cart")

    def test_apply_coupon_below_minimum_order_value(self):
        # Vehicle is 3.8M, coupon requires 5.0M min order
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})
        response = self.client.post(
            reverse('cart:coupon_apply'),
            {'code': 'HIGHMIN'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minimum order valuation of $5,000,000.00 is required")
        session = self.client.session
        self.assertIsNone(session.get('aurevia_applied_coupon'))

    def test_remove_coupon_workflow(self):
        # 1. Add vehicle and apply coupon
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})
        self.client.post(reverse('cart:coupon_apply'), {'code': 'FIRST50'})

        # 2. Remove coupon
        response = self.client.post(reverse('cart:coupon_remove'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Promotional voucher removed from your order")

        session = self.client.session
        self.assertIsNone(session.get('aurevia_applied_coupon'))

    def test_cart_detail_auto_clears_invalidated_coupon_if_condition_changes(self):
        # 1. Add 2 units of vehicle = 7.6M (qualifies for HIGHMIN)
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 2})
        self.client.post(reverse('cart:coupon_apply'), {'code': 'HIGHMIN'})
        self.assertEqual(self.client.session.get('aurevia_applied_coupon'), 'HIGHMIN')

        # 2. Update cart quantity to 1 unit = 3.8M (below 5M minimum)
        self.client.post(reverse('cart:cart_update', args=[self.vehicle.id]), {'quantity': 1})

        # 3. Visit cart detail -> should detect coupon is no longer valid and clear it
        response = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applied coupon was removed")
        self.assertIsNone(self.client.session.get('aurevia_applied_coupon'))

    def test_cart_clear_clears_coupon(self):
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})
        self.client.post(reverse('cart:coupon_apply'), {'code': 'FIRST50'})
        self.assertEqual(self.client.session.get('aurevia_applied_coupon'), 'FIRST50')

        self.client.get(reverse('cart:cart_clear'))
        self.assertIsNone(self.client.session.get('aurevia_applied_coupon'))


class CheckoutFlowTests(TestCase):
    """
    Test suite for checkout review, address resolution, atomic order placement, and inventory guards.
    """

    def setUp(self):
        self.client = Client()
        self.password = "AureviaSecret2026!"
        self.user = User.objects.create_user(
            username="client_arthur",
            email="arthur@atelier.com",
            password=self.password
        )
        self.other_user = User.objects.create_user(
            username="client_other",
            email="other@atelier.com",
            password=self.password
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name="Arthur Pendelton",
            street_line_1="742 Evergreen Terrace",
            city="Monaco",
            state_or_province="Monte Carlo",
            postal_code="98000",
            country="Monaco",
            is_default=True
        )
        self.other_address = Address.objects.create(
            user=self.other_user,
            full_name="Eve Hacker",
            street_line_1="10 Downing St",
            city="London",
            state_or_province="Greater London",
            postal_code="SW1A 2AA",
            country="United Kingdom"
        )
        self.brand = Brand.objects.create(name="Bugatti", slug="bugatti", country="France")
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model_name="Chiron Pur Sport",
            slug="chiron-pur-sport",
            year=2024,
            price=Decimal('3800000.00'),
            currency='USD',
            status=Vehicle.STATUS_AVAILABLE,
        )

    def test_checkout_view_requires_login(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_checkout_view_redirects_empty_cart(self):
        self.client.login(username="client_arthur", password=self.password)
        response = self.client.get(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('catalog:vehicle_list'))

    def test_checkout_view_renders_line_items_and_saved_addresses(self):
        self.client.login(username="client_arthur", password=self.password)
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})

        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chiron Pur Sport")
        self.assertContains(response, "742 Evergreen Terrace")
        self.assertContains(response, "Concierge Escrow & Bank Wire")
        self.assertContains(response, "Web3 / MetaMask Ethereum")

    def test_checkout_process_creates_order_items_and_payment_atomically(self):
        self.client.login(username="client_arthur", password=self.password)
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})

        # Apply coupon
        now = timezone.now()
        coupon = Coupon.objects.create(
            code="FIRST50",
            discount_type=Coupon.DISCOUNT_PERCENTAGE,
            discount_value=Decimal('5.00'),
            min_order_value=Decimal('100000.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        self.client.post(reverse('cart:coupon_apply'), {'code': 'FIRST50'})

        # Post checkout submission
        response = self.client.post(
            reverse('orders:checkout_process'),
            {
                'address_id': self.address.id,
                'payment_method': Payment.METHOD_BANK_WIRE,
                'client_notes': 'Please deliver inside the climate-controlled hangar.',
            }
        )

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('orders:payment_detail', args=[order.order_number]))

        # Verify Order data
        self.assertEqual(order.status, Order.STATUS_AWAITING_PAYMENT)
        self.assertEqual(order.shipping_full_name, "Arthur Pendelton")
        self.assertEqual(order.subtotal, Decimal('3800000.00'))
        self.assertEqual(order.discount_amount, Decimal('190000.00'))
        self.assertEqual(order.grand_total, Decimal('3610000.00'))
        self.assertEqual(order.coupon, coupon)

        # Verify OrderItem snapshot
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.vehicle, self.vehicle)
        self.assertEqual(item.vehicle_model_name, "Chiron Pur Sport")
        self.assertEqual(item.unit_price, Decimal('3800000.00'))
        self.assertEqual(item.quantity, 1)

        # Verify Payment ledger record
        self.assertTrue(hasattr(order, 'payment'))
        payment = order.payment
        self.assertEqual(payment.payment_method, Payment.METHOD_BANK_WIRE)
        self.assertEqual(payment.amount, Decimal('3610000.00'))
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        self.assertTrue(payment.escrow_reference.startswith('ESC-'))

        # Verify coupon usage increment
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)

        # Verify cart was cleared
        cart = Cart(response.wsgi_request)
        self.assertTrue(cart.is_empty)

    def test_checkout_process_with_unowned_address_returns_404(self):
        self.client.login(username="client_arthur", password=self.password)
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})

        # Try to use other_address belonging to Eve Hacker
        response = self.client.post(
            reverse('orders:checkout_process'),
            {
                'address_id': self.other_address.id,
                'payment_method': Payment.METHOD_BANK_WIRE,
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_checkout_process_with_inline_manual_address(self):
        self.client.login(username="client_arthur", password=self.password)
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})

        response = self.client.post(
            reverse('orders:checkout_process'),
            {
                'address_id': '',  # No saved address
                'full_name': 'Count Ferdinand',
                'phone': '+33 6 12 34 56 78',
                'address_line_1': 'Château de Saint-Jean',
                'address_line_2': 'North Gate',
                'city': 'Molsheim',
                'state_province': 'Alsace',
                'postal_code': '67120',
                'country': 'France',
                'payment_method': Payment.METHOD_CRYPTO_ETH,
            }
        )

        order = Order.objects.filter(shipping_full_name='Count Ferdinand').first()
        self.assertIsNotNone(order)
        self.assertRedirects(response, reverse('orders:payment_detail', args=[order.order_number]))
        self.assertEqual(order.shipping_city, 'Molsheim')
        self.assertEqual(order.payment.payment_method, Payment.METHOD_CRYPTO_ETH)

    def test_checkout_process_aborts_if_vehicle_becomes_unavailable(self):
        self.client.login(username="client_arthur", password=self.password)
        self.client.post(reverse('cart:cart_add', args=[self.vehicle.id]), {'quantity': 1})

        # Vehicle is sold right before checkout execution
        self.vehicle.status = Vehicle.STATUS_SOLD
        self.vehicle.save()

        response = self.client.post(
            reverse('orders:checkout_process'),
            {
                'address_id': self.address.id,
                'payment_method': Payment.METHOD_BANK_WIRE,
            },
            follow=True
        )
        self.assertRedirects(response, reverse('cart:cart_detail'))
        self.assertContains(response, "is no longer available for reservation")
        self.assertEqual(Order.objects.count(), 0)


class PaymentRailTests(TestCase):
    """
    Test suite for payment state machines, wire confirmations, and access control.
    """

    def setUp(self):
        self.client = Client()
        self.password = "AureviaSecret2026!"
        self.user = User.objects.create_user(username="client_arthur", password=self.password)
        self.other_user = User.objects.create_user(username="client_other", password=self.password)
        self.order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_AWAITING_PAYMENT,
            shipping_full_name="Arthur Pendelton",
            shipping_phone="+1 555-019-2834",
            shipping_address_line_1="742 Evergreen Terrace",
            shipping_city="Monaco",
            shipping_state_province="Monte Carlo",
            shipping_postal_code="98000",
            shipping_country="Monaco",
            subtotal=Decimal('3800000.00'),
            grand_total=Decimal('3800000.00'),
            currency='USD'
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method=Payment.METHOD_BANK_WIRE,
            amount=Decimal('3800000.00'),
            status=Payment.STATUS_PENDING
        )

    def test_payment_detail_view_requires_login_and_ownership(self):
        # 1. Anonymous access
        url = reverse('orders:payment_detail', args=[self.order.order_number])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # 2. Other user access (cross-user violation) -> 404
        self.client.login(username="client_other", password=self.password)
        response_other = self.client.get(url)
        self.assertEqual(response_other.status_code, 404)

        # 3. Legitimate user access -> 200
        self.client.login(username="client_arthur", password=self.password)
        response_owner = self.client.get(url)
        self.assertEqual(response_owner.status_code, 200)
        self.assertContains(response_owner, self.order.order_number)

    def test_payment_confirm_wire_transitions_to_submitted(self):
        self.client.login(username="client_arthur", password=self.password)
        url = reverse('orders:payment_confirm_wire', args=[self.order.order_number])
        response = self.client.post(url, follow=True)

        self.assertRedirects(response, reverse('orders:order_confirmation', args=[self.order.order_number]))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_SUBMITTED)
        self.assertIn("wire transfer dispatch", self.payment.verification_notes.lower())

    def test_payment_mark_as_confirmed_updates_order_to_paid(self):
        self.payment.mark_as_confirmed(notes="Escrow funds settled via JPMorgan wire.")
        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.STATUS_CONFIRMED)
        self.assertIsNotNone(self.payment.verified_at)
        self.assertEqual(self.order.status, Order.STATUS_PAID)

    def test_payment_mark_as_failed_records_reason(self):
        self.payment.mark_as_failed("Insufficient funds.")
        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.STATUS_FAILED)
        self.assertEqual(self.payment.verification_notes, "Insufficient funds.")
        self.assertNotEqual(self.order.status, Order.STATUS_PAID)


class CryptoPaymentSecurityTests(TestCase):
    """
    Test suite for Web3 / Ethereum cryptographic verification, anti-tampering,
    replay protection, unconfigured RPC honesty, and private key safety.
    """

    def setUp(self):
        self.client = Client()
        self.password = "AureviaSecret2026!"
        self.user = User.objects.create_user(username="crypto_whale", password=self.password)
        self.order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_AWAITING_PAYMENT,
            shipping_full_name="Satoshi Nakamoto",
            shipping_phone="+1 555-010-0000",
            shipping_address_line_1="Genesis Block Tower",
            shipping_city="Zug",
            shipping_state_province="Crypto Valley",
            shipping_postal_code="6300",
            shipping_country="Switzerland",
            subtotal=Decimal('3000000.00'),
            grand_total=Decimal('3000000.00'),
            currency='USD'
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method=Payment.METHOD_CRYPTO_ETH,
            amount=Decimal('3000000.00'),
            status=Payment.STATUS_PENDING
        )
        self.valid_tx_hash = "0x" + "a" * 64

    def test_crypto_verification_invalid_format_rejected(self):
        for bad_hash in ["not-a-hash", "0x1234", "0x" + "z" * 64]:
            verified, reason = PaymentVerificationService.verify_crypto_payment(
                payment=self.payment,
                tx_hash=bad_hash
            )
            self.assertFalse(verified)
            self.assertIn("Invalid Ethereum transaction hash format", reason)

        for empty_hash in ["", "   ", None]:
            verified, reason = PaymentVerificationService.verify_crypto_payment(
                payment=self.payment,
                tx_hash=empty_hash
            )
            self.assertFalse(verified)
            self.assertIn("required", reason.lower())

    def test_crypto_verification_replay_attack_rejected(self):
        # Create a pre-existing payment with the same tx_hash
        other_order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_PAID,
            shipping_full_name="Existing Customer",
            shipping_phone="123",
            shipping_address_line_1="Addr",
            shipping_city="City",
            shipping_state_province="State",
            shipping_postal_code="12345",
            shipping_country="Country",
            subtotal=Decimal('1000000.00'),
            grand_total=Decimal('1000000.00')
        )
        Payment.objects.create(
            order=other_order,
            payment_method=Payment.METHOD_CRYPTO_ETH,
            amount=Decimal('1000000.00'),
            status=Payment.STATUS_CONFIRMED,
            transaction_hash=self.valid_tx_hash
        )

        # Attacker tries to submit the same tx_hash for self.payment
        verified, reason = PaymentVerificationService.verify_crypto_payment(
            payment=self.payment,
            tx_hash=self.valid_tx_hash
        )
        self.assertFalse(verified)
        self.assertIn("already been used", reason)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_FAILED)
        self.assertIn("Replay attack detected", self.payment.verification_notes)

    @override_settings(ETHEREUM_RPC_URL='')
    def test_crypto_verification_unconfigured_rpc_halts_without_false_success(self):
        # When RPC is unconfigured, system halts verification honestly and does NOT mark as paid.
        verified, reason = PaymentVerificationService.verify_crypto_payment(
            payment=self.payment,
            tx_hash=self.valid_tx_hash,
            wallet_address="0x1234567890123456789012345678901234567890"
        )
        self.assertFalse(verified)
        self.assertIn("concierge mode", reason.lower())

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        # Must NOT be marked CONFIRMED or PAID
        self.assertEqual(self.payment.status, Payment.STATUS_SUBMITTED)
        self.assertNotEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(self.payment.transaction_hash, self.valid_tx_hash)
        self.assertIn("Automated cryptographic verification halted", self.payment.verification_notes)

    @override_settings(
        ETHEREUM_RPC_URL='https://eth-mainnet.alchemyapi.io/v2/mock',
        ETHEREUM_SETTLEMENT_ADDRESS='0xSettlementDestination12345678901234'
    )
    @patch('urllib.request.urlopen')
    def test_crypto_verification_rpc_mocked_success(self, mock_urlopen):
        # Mock eth_getTransactionByHash response
        tx_mock_response = MagicMock()
        tx_mock_response.__enter__.return_value.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "hash": self.valid_tx_hash,
                "from": "0xClientSigner1234567890",
                "to": "0xSettlementDestination12345678901234",
                "value": "0x1234"
            }
        }).encode('utf-8')

        # Mock eth_getTransactionReceipt response
        receipt_mock_response = MagicMock()
        receipt_mock_response.__enter__.return_value.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "transactionHash": self.valid_tx_hash,
                "blockNumber": "0x10d4f23",
                "status": "0x1",  # EVM execution success
                "gasUsed": "0x5208"
            }
        }).encode('utf-8')

        mock_urlopen.side_effect = [tx_mock_response, receipt_mock_response]

        verified, reason = PaymentVerificationService.verify_crypto_payment(
            payment=self.payment,
            tx_hash=self.valid_tx_hash,
            wallet_address="0xClientSigner1234567890"
        )

        self.assertTrue(verified)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.STATUS_CONFIRMED)
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertIn("Cryptographically verified", self.payment.verification_notes)

    @override_settings(
        ETHEREUM_RPC_URL='https://eth-mainnet.alchemyapi.io/v2/mock',
        ETHEREUM_SETTLEMENT_ADDRESS='0xSettlementDestination12345678901234'
    )
    @patch('urllib.request.urlopen')
    def test_crypto_verification_rpc_mocked_revert_fails(self, mock_urlopen):
        # Mock tx found
        tx_mock = MagicMock()
        tx_mock.__enter__.return_value.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "hash": self.valid_tx_hash,
                "to": "0xSettlementDestination12345678901234"
            }
        }).encode('utf-8')

        # Mock receipt with status 0x0 (EVM execution reverted)
        receipt_mock = MagicMock()
        receipt_mock.__enter__.return_value.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "transactionHash": self.valid_tx_hash,
                "blockNumber": "0x10d4f23",
                "status": "0x0"  # Reverted
            }
        }).encode('utf-8')

        mock_urlopen.side_effect = [tx_mock, receipt_mock]

        verified, reason = PaymentVerificationService.verify_crypto_payment(
            payment=self.payment,
            tx_hash=self.valid_tx_hash
        )

        self.assertFalse(verified)
        self.assertIn("reverted on-chain", reason)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_FAILED)

    def test_zero_private_keys_stored(self):
        # Verify that models do not have private key or seed phrase fields
        for field in Payment._meta.get_fields():
            self.assertNotIn('private', field.name.lower())
            self.assertNotIn('seed', field.name.lower())
            self.assertNotIn('secret', field.name.lower())

        for field in Order._meta.get_fields():
            self.assertNotIn('private', field.name.lower())
            self.assertNotIn('seed', field.name.lower())
            self.assertNotIn('secret', field.name.lower())

    def test_client_cannot_spoof_payment_status(self):
        # Attempt to post spoofed payment status
        self.client.login(username="crypto_whale", password=self.password)
        url = reverse('orders:payment_detail', args=[self.order.order_number])

        # Post with malicious status=confirmed parameter
        self.client.post(url, {'status': 'confirmed', 'paid': True})
        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.STATUS_PENDING)
        self.assertEqual(self.order.status, Order.STATUS_AWAITING_PAYMENT)

