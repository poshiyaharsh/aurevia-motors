from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.catalog.models import Brand, Vehicle
from apps.orders.models import Coupon
from apps.orders.pricing import PricingEngine, OrderCalculationResult
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
