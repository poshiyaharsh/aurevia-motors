from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from django.conf import settings
from .models import Coupon


@dataclass(frozen=True)
class OrderCalculationResult:
    """
    Immutable representation of an authoritative server-calculated order breakdown.
    All monetary attributes are Decimal values quantized to two decimal places.
    """
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    delivery_fee: Decimal
    grand_total: Decimal
    coupon: Optional[Coupon] = None
    coupon_code: Optional[str] = None
    is_coupon_applied: bool = False
    coupon_rejection_reason: Optional[str] = None
    currency: str = 'USD'

    @property
    def has_discount(self) -> bool:
        return self.is_coupon_applied and self.discount_amount > Decimal('0.00')


class PricingEngine:
    """
    Authoritative server-side pricing engine.
    Ensures zero client trust, decimal-safe arithmetic (ROUND_HALF_UP),
    non-negative totals, and strict coupon restriction enforcement.
    """

    @classmethod
    def get_tax_rate(cls) -> Decimal:
        """
        Retrieves the configured tax rate from settings.
        Defaults to Decimal('0.00') unless explicitly defined in settings.
        """
        raw_rate = getattr(settings, 'ORDER_TAX_RATE', Decimal('0.00'))
        return Decimal(str(raw_rate))

    @classmethod
    def get_delivery_fee(cls) -> Decimal:
        """
        Retrieves the delivery/logistics fee from settings.
        Defaults to Decimal('0.00') (complimentary white-glove transport).
        """
        raw_fee = getattr(settings, 'ORDER_DELIVERY_FEE', Decimal('0.00'))
        return Decimal(str(raw_fee)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate(
        cls,
        subtotal: Decimal,
        coupon_code: Optional[str] = None,
        currency: str = 'USD'
    ) -> OrderCalculationResult:
        """
        Performs authoritative server-side calculation for a given subtotal and optional coupon code.
        """
        subtotal = Decimal(str(subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if subtotal < Decimal('0.00'):
            subtotal = Decimal('0.00')

        discount_amount = Decimal('0.00')
        applied_coupon = None
        coupon_rejection_reason = None
        is_coupon_applied = False

        if coupon_code and coupon_code.strip():
            cleaned_code = coupon_code.strip().upper()
            try:
                coupon = Coupon.objects.get(code=cleaned_code)
                is_valid, reason = coupon.can_apply(subtotal=subtotal)
                if is_valid:
                    discount_amount = coupon.calculate_discount(subtotal=subtotal)
                    applied_coupon = coupon
                    is_coupon_applied = True
                else:
                    coupon_rejection_reason = reason
            except Coupon.DoesNotExist:
                coupon_rejection_reason = f"Promotional code '{cleaned_code}' does not exist."

        # Tax calculation on net taxable amount
        taxable_amount = max(Decimal('0.00'), subtotal - discount_amount)
        tax_rate = cls.get_tax_rate()
        tax_amount = (taxable_amount * tax_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        delivery_fee = cls.get_delivery_fee()

        # Grand total strictly bounded at or above 0.00
        raw_total = subtotal - discount_amount + tax_amount + delivery_fee
        grand_total = max(Decimal('0.00'), raw_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return OrderCalculationResult(
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            grand_total=grand_total,
            coupon=applied_coupon,
            coupon_code=coupon_code.strip().upper() if coupon_code else None,
            is_coupon_applied=is_coupon_applied,
            coupon_rejection_reason=coupon_rejection_reason,
            currency=currency,
        )

    @classmethod
    def calculate_cart(cls, cart, coupon_code: Optional[str] = None) -> OrderCalculationResult:
        """
        Helper method to compute pricing directly from an active Cart instance.
        Queries database prices to guarantee client-side price tampering resistance.
        """
        subtotal = cart.get_total_price()
        return cls.calculate(subtotal=subtotal, coupon_code=coupon_code)
