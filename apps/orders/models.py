from decimal import Decimal, ROUND_HALF_UP
import uuid
from django.conf import settings
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


class Order(models.Model):
    """
    Authoritative order record for luxury vehicle acquisitions.
    Stores immutable snapshots of client details, delivery address, line items, and server pricing.
    """
    STATUS_PENDING = 'pending'
    STATUS_AWAITING_PAYMENT = 'awaiting_payment'
    STATUS_PAID = 'paid'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Checkout'),
        (STATUS_AWAITING_PAYMENT, 'Awaiting Settlement'),
        (STATUS_PAID, 'Payment Confirmed / Paid'),
        (STATUS_PROCESSING, 'Allocation Processing & Title Prep'),
        (STATUS_COMPLETED, 'Delivery Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    order_number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Unique atelier order identification number (e.g. AUM-20261106-ABCD12)."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        help_text="Acquiring customer."
    )
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )

    # Delivery Address Snapshot (immutable historical record)
    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=32)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state_province = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Financial breakdown snapshot (immutable Decimal records)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    coupon_code_snapshot = models.CharField(max_length=30, blank=True)

    client_notes = models.TextField(blank=True, help_text="Special concierge handling or delivery instructions.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Atelier Acquisition Order'
        verbose_name_plural = 'Atelier Acquisition Orders'

    def __str__(self):
        return f"Order {self.order_number} ({self.get_status_display()}) - {self.currency} {self.grand_total:,.2f}"

    @classmethod
    def generate_order_number(cls):
        date_str = timezone.now().strftime('%Y%m%d')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"AUM-{date_str}-{unique_suffix}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """
    Immutable historical line item snapshot for an atelier order.
    Preserves exact purchase-time vehicle specifications and unit prices.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    vehicle = models.ForeignKey(
        'catalog.Vehicle',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    # Immutable historical vehicle snapshot
    vehicle_model_name = models.CharField(max_length=150)
    vehicle_brand_name = models.CharField(max_length=100)
    vehicle_year = models.PositiveIntegerField()
    vehicle_vin = models.CharField(max_length=17, blank=True, default='')

    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'Order Line Item'
        verbose_name_plural = 'Order Line Items'

    def __str__(self):
        return f"{self.quantity}x {self.vehicle_year} {self.vehicle_brand_name} {self.vehicle_model_name}"


class Payment(models.Model):
    """
    Cryptographic and escrow payment ledger record.
    Tracks multi-rail transactions with replay prevention, status state machines,
    and audit trails.
    """
    METHOD_BANK_WIRE = 'bank_wire'
    METHOD_CRYPTO_ETH = 'crypto_ethereum'

    PAYMENT_METHOD_CHOICES = [
        (METHOD_BANK_WIRE, 'Concierge Escrow & Bank Wire'),
        (METHOD_CRYPTO_ETH, 'Web3 / MetaMask Ethereum Settlement'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SUBMITTED = 'submitted'
    STATUS_VERIFYING = 'verifying'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    PAYMENT_STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Action'),
        (STATUS_SUBMITTED, 'Settlement Submitted by Client'),
        (STATUS_VERIFYING, 'Verifying On-Chain / Banking Receipt'),
        (STATUS_CONFIRMED, 'Confirmed & Cleared'),
        (STATUS_FAILED, 'Verification Failed / Rejected'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='payment',
        help_text="Order associated with this payment record."
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default=METHOD_BANK_WIRE
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Authoritative server-calculated settlement amount."
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    escrow_reference = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Unique atelier escrow reference code for wire identification."
    )
    transaction_hash = models.CharField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Blockchain transaction hash (EVM tx hash, unique to prevent replay attacks)."
    )
    wallet_address = models.CharField(
        max_length=64,
        blank=True,
        help_text="Public wallet address initiating payment (NEVER store private keys)."
    )
    chain_id = models.CharField(
        max_length=32,
        blank=True,
        help_text="Target EVM chain ID where transaction was broadcast."
    )
    verification_notes = models.TextField(
        blank=True,
        help_text="Audit and verification logs from banking or RPC queries."
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Settlement Record'
        verbose_name_plural = 'Payment Settlement Records'

    def __str__(self):
        return f"Payment {self.escrow_reference} for Order {self.order.order_number} ({self.get_status_display()})"

    @classmethod
    def generate_escrow_reference(cls):
        date_str = timezone.now().strftime('%Y%m%d')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"ESC-{date_str}-{unique_suffix}"

    def save(self, *args, **kwargs):
        if not self.escrow_reference:
            self.escrow_reference = self.generate_escrow_reference()
        super().save(*args, **kwargs)

    def mark_as_confirmed(self, notes=None):
        """
        Transitions payment to CONFIRMED status and marks parent order as PAID.
        """
        self.status = self.STATUS_CONFIRMED
        self.verified_at = timezone.now()
        if notes:
            self.verification_notes = notes
        self.save()

        # Update parent order
        self.order.status = Order.STATUS_PAID
        self.order.save()

    def mark_as_failed(self, reason):
        """
        Transitions payment to FAILED status with recorded reason.
        """
        self.status = self.STATUS_FAILED
        self.verification_notes = reason
        self.save()

