from django.contrib import admin
from .models import Coupon


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
