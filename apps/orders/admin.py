from django.contrib import admin
from .models import Coupon, Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        'vehicle',
        'vehicle_brand_name',
        'vehicle_model_name',
        'vehicle_year',
        'vehicle_vin',
        'unit_price',
        'quantity',
        'line_total'
    )
    can_delete = False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ('escrow_reference', 'created_at', 'updated_at', 'verified_at')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'status',
        'grand_total',
        'currency',
        'created_at',
    )
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'shipping_full_name')
    readonly_fields = (
        'order_number',
        'subtotal',
        'discount_amount',
        'tax_amount',
        'delivery_fee',
        'grand_total',
        'currency',
        'created_at',
        'updated_at',
    )
    inlines = [OrderItemInline, PaymentInline]

    fieldsets = (
        ('Order Identification', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Delivery Address Snapshot', {
            'fields': (
                'shipping_full_name',
                'shipping_phone',
                'shipping_address_line_1',
                'shipping_address_line_2',
                'shipping_city',
                'shipping_state_province',
                'shipping_postal_code',
                'shipping_country',
            )
        }),
        ('Financial Breakdown Snapshot', {
            'fields': (
                'subtotal',
                'discount_amount',
                'tax_amount',
                'delivery_fee',
                'grand_total',
                'currency',
                'coupon',
                'coupon_code_snapshot',
            )
        }),
        ('Concierge Instructions', {
            'fields': ('client_notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'escrow_reference',
        'order',
        'payment_method',
        'amount',
        'currency',
        'status',
        'transaction_hash',
        'verified_at',
    )
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('escrow_reference', 'transaction_hash', 'wallet_address', 'order__order_number')
    readonly_fields = ('escrow_reference', 'created_at', 'updated_at', 'verified_at')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_type',
        'discount_value',
        'min_order_value',
        'max_discount_amount',
        'valid_from',
        'valid_to',
        'used_count',
        'max_uses',
        'is_active',
    )
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('used_count', 'created_at', 'updated_at')

    fieldsets = (
        ('Voucher Identity', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Configuration', {
            'fields': ('discount_type', 'discount_value', 'min_order_value', 'max_discount_amount')
        }),
        ('Validity Window & Limits', {
            'fields': ('valid_from', 'valid_to', 'max_uses', 'used_count')
        }),
        ('Audit Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
