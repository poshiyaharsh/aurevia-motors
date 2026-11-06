from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.orders.models import Coupon


class Command(BaseCommand):
    help = "Seeds initial luxury promotional vouchers and coupons for Aurevia Motors."

    def handle(self, *args, **options):
        now = timezone.now()

        coupons_data = [
            {
                'code': 'FIRST50',
                'description': 'Inaugural Client Privilege — 5% allocation concession',
                'discount_type': Coupon.DISCOUNT_PERCENTAGE,
                'discount_value': Decimal('5.00'),
                'min_order_value': Decimal('100000.00'),
                'max_discount_amount': Decimal('50000.00'),
                'valid_from': now - timedelta(days=1),
                'valid_to': now + timedelta(days=365),
                'max_uses': 50,
                'is_active': True,
            },
            {
                'code': 'VIPATELIER',
                'description': 'Private Atelier Concession — $50,000 fixed allocation credit',
                'discount_type': Coupon.DISCOUNT_FIXED,
                'discount_value': Decimal('50000.00'),
                'min_order_value': Decimal('500000.00'),
                'max_discount_amount': None,
                'valid_from': now - timedelta(days=1),
                'valid_to': now + timedelta(days=365),
                'max_uses': 20,
                'is_active': True,
            },
            {
                'code': 'ROYALTY10',
                'description': 'Royalty Allocation Concession — 10% concession capped at $150,000',
                'discount_type': Coupon.DISCOUNT_PERCENTAGE,
                'discount_value': Decimal('10.00'),
                'min_order_value': Decimal('1000000.00'),
                'max_discount_amount': Decimal('150000.00'),
                'valid_from': now - timedelta(days=1),
                'valid_to': now + timedelta(days=365),
                'max_uses': 10,
                'is_active': True,
            },
            {
                'code': 'EXPIRED2025',
                'description': 'Legacy Archive Voucher (Expired test voucher)',
                'discount_type': Coupon.DISCOUNT_FIXED,
                'discount_value': Decimal('25000.00'),
                'min_order_value': Decimal('100000.00'),
                'max_discount_amount': None,
                'valid_from': now - timedelta(days=365),
                'valid_to': now - timedelta(days=1),
                'max_uses': 10,
                'is_active': True,
            },
            {
                'code': 'INACTIVEVIP',
                'description': 'Suspended Atelier Voucher (Inactive test voucher)',
                'discount_type': Coupon.DISCOUNT_PERCENTAGE,
                'discount_value': Decimal('15.00'),
                'min_order_value': Decimal('250000.00'),
                'max_discount_amount': None,
                'valid_from': now - timedelta(days=1),
                'valid_to': now + timedelta(days=365),
                'max_uses': 5,
                'is_active': False,
            },
        ]

        created_count = 0
        updated_count = 0

        for c_data in coupons_data:
            code = c_data.pop('code')
            coupon, created = Coupon.objects.update_or_create(
                code=code,
                defaults=c_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created coupon: {coupon}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Updated coupon: {coupon}"))

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded coupons! ({created_count} created, {updated_count} updated)."
        ))
