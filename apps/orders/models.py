from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Coupon(models.Model):
    """
    Promotional and VIP allocation vouchers for supercars and hypercars.
    Supports percentage-based and fixed-amount discounts with strict validation rules.
    """
    DISCOUNT_PERCENTAGE = 'percentage'
    DISCOUNT_FIXED = 'fixed'

    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENTAGE, 'Percentage Discount (%)'),
        (DISCOUNT_FIXED, 'Fixed Amount Discount ($)'),
    ]

    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Unique voucher/coupon code (alphanumeric, auto-uppercased)."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Internal notes or client-facing description (e.g. VIP Concierge Allocation)."
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_PERCENTAGE,
        help_text="Specifies whether the discount is a percentage or fixed currency amount."
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Discount value: percentage rate (e.g. 5.00 for 5%) or fixed amount (e.g. 50000.00)."
    )
    min_order_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum subtotal required to apply this coupon."
    )
    max_discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Maximum discount cap for percentage discounts. Leave blank for uncapped."
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the coupon becomes active."
    )
    valid_to = models.DateTimeField(
        help_text="Date and time when the coupon expires."
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total allowed redemptions across all clients. Leave blank for unlimited."
    )
    used_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of completed orders that used this coupon."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Active status toggle (kill switch)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Coupon & Voucher'
        verbose_name_plural = 'Coupons & Vouchers'

    def __str__(self):
        if self.discount_type == self.DISCOUNT_PERCENTAGE:
            return f"{self.code} ({self.discount_value}% OFF)"
        return f"{self.code} (${self.discount_value:,.2f} OFF)"

    def clean(self):
        """
        Validates model integrity constraints.
        """
        if self.code:
            self.code = self.code.strip().upper()

        if self.valid_from and self.valid_to:
            if self.valid_to <= self.valid_from:
                raise ValidationError({
                    'valid_to': "Expiration date (valid_to) must be chronologically after the start date (valid_from)."
                })

        if self.discount_type == self.DISCOUNT_PERCENTAGE:
            if self.discount_value > Decimal('100.00'):
                raise ValidationError({
                    'discount_value': "Percentage discount cannot exceed 100%."
                })
            if self.discount_value <= Decimal('0.00'):
                raise ValidationError({
                    'discount_value': "Percentage discount must be greater than 0%."
                })

        if self.discount_type == self.DISCOUNT_FIXED:
            if self.discount_value <= Decimal('0.00'):
                raise ValidationError({
                    'discount_value': "Fixed discount must be greater than $0.00."
                })

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        self.clean()
        super().save(*args, **kwargs)

    def can_apply(self, subtotal=None):
        """
        Validates whether this coupon can be applied given the current subtotal and status.
        Returns a tuple (is_valid: bool, reason: str).
        """
        if not self.is_active:
            return False, "This promotional coupon is inactive."

        now = timezone.now()
        if now < self.valid_from:
            return False, "This promotional code is not yet active."

        if now > self.valid_to:
            return False, "This promotional code has expired."

        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "This promotional coupon has reached its maximum redemption limit."

        if subtotal is not None:
            subtotal_dec = Decimal(str(subtotal))
            if subtotal_dec <= Decimal('0.00'):
                return False, "Cannot apply a coupon to an empty or zero-value cart."
            if subtotal_dec < self.min_order_value:
                return False, (
                    f"Minimum order valuation of ${self.min_order_value:,.2f} is required "
                    f"to apply this coupon."
                )

        return True, "Coupon is valid."

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """
        Calculates the exact discount for a given subtotal using decimal arithmetic and ROUND_HALF_UP.
        Guarantees discount does not exceed subtotal and is never negative.
        """
        if subtotal <= Decimal('0.00'):
            return Decimal('0.00')

        if self.discount_type == self.DISCOUNT_PERCENTAGE:
            raw_discount = (subtotal * self.discount_value) / Decimal('100.00')
            if self.max_discount_amount is not None:
                raw_discount = min(raw_discount, self.max_discount_amount)
        elif self.discount_type == self.DISCOUNT_FIXED:
            raw_discount = self.discount_value
        else:
            return Decimal('0.00')

        # Clamp discount so total never goes below zero
        discount = min(raw_discount, subtotal)
        discount = max(Decimal('0.00'), discount)
        return discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
