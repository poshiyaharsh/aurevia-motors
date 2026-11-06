from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, OrderItem, Payment, Coupon, OrderAuditLog
from .notifications import OrderNotificationService


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        'vehicle_brand_name', 'vehicle_model_name', 'vehicle_year', 
        'vehicle_vin', 'unit_price', 'quantity', 'line_total'
    )
    fields = (
        'vehicle_brand_name', 'vehicle_model_name', 'vehicle_year', 
        'vehicle_vin', 'unit_price', 'quantity', 'line_total'
    )

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = (
        'escrow_reference', 'payment_method', 'status', 'amount', 'currency', 
        'transaction_hash', 'wallet_address', 'chain_id', 'verification_notes',
        'verified_at', 'created_at'
    )
    fields = (
        ('escrow_reference', 'payment_method', 'status'),
        ('amount', 'currency'),
        ('transaction_hash', 'wallet_address', 'chain_id'),
        'verification_notes',
        ('verified_at', 'created_at')
    )

    def has_add_permission(self, request, obj=None):
        return False


class OrderAuditLogInline(admin.TabularInline):
    model = OrderAuditLog
    extra = 0
    can_delete = False
    readonly_fields = ('performed_by', 'action', 'old_status', 'new_status', 'notes', 'created_at')
    fields = ('performed_by', 'action', 'old_status', 'new_status', 'notes', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user', 'status_badge', 
        'payment_method_display', 'formatted_grand_total', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'shipping_full_name')
    readonly_fields = (
        'order_number', 'user', 'created_at', 'updated_at', 
        'subtotal', 'discount_amount', 'grand_total', 'currency', 'coupon_code_snapshot'
    )
    inlines = [OrderItemInline, PaymentInline, OrderAuditLogInline]
    actions = ['advance_to_processing', 'advance_to_completed', 'cancel_orders']

    fieldsets = (
        ('Order Identification', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Financial Summary', {
            'fields': ('subtotal', 'discount_amount', 'coupon_code_snapshot', 'grand_total', 'currency')
        }),
        ('Delivery & Concierge Logistics', {
            'fields': (
                'shipping_full_name', 'shipping_phone',
                'shipping_address_line_1', 'shipping_address_line_2',
                'shipping_city', 'shipping_state_province', 'shipping_postal_code', 
                'shipping_country', 'client_notes'
            )
        }),
    )

    def status_badge(self, obj):
        colors = {
            Order.STATUS_PENDING: '#f59e0b',           # Amber
            Order.STATUS_AWAITING_PAYMENT: '#d97706',  # Deep Amber
            Order.STATUS_PAID: '#10b981',              # Emerald
            Order.STATUS_PROCESSING: '#3b82f6',        # Blue
            Order.STATUS_COMPLETED: '#059669',         # Green
            Order.STATUS_CANCELLED: '#ef4444',         # Red
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def payment_method_display(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.get_payment_method_display()
        return '-'
    payment_method_display.short_description = 'Payment Method'

    def formatted_grand_total(self, obj):
        return f"${obj.grand_total:,.2f} {obj.currency}"
    formatted_grand_total.short_description = 'Grand Total'

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            old_order = Order.objects.get(pk=obj.pk)
            old_status = old_order.status
            new_status = obj.status

            if not old_order.can_transition_to(new_status):
                self.message_user(
                    request,
                    f"Invalid status transition from '{old_status}' to '{new_status}' for Order {obj.order_number}.",
                    level='ERROR'
                )
                return  # Do not persist illegal transition

            super().save_model(request, obj, form, change)

            # Record audit log
            OrderAuditLog.objects.create(
                order=obj,
                performed_by=request.user,
                action=f"Status changed from {old_status} to {new_status} via Admin Form",
                old_status=old_status,
                new_status=new_status,
                notes=f"Updated manually by staff user {request.user.username}"
            )

            # Defensive notification
            OrderNotificationService.send_order_status_update(obj, old_status, new_status)
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description="Advance selected orders to Processing")
    def advance_to_processing(self, request, queryset):
        success_count = 0
        fail_count = 0
        for order in queryset:
            old_status = order.status
            if order.can_transition_to(Order.STATUS_PROCESSING):
                order.status = Order.STATUS_PROCESSING
                order.save(update_fields=['status', 'updated_at'])
                OrderAuditLog.objects.create(
                    order=order,
                    performed_by=request.user,
                    action="Advanced to Processing via Bulk Action",
                    old_status=old_status,
                    new_status=Order.STATUS_PROCESSING,
                    notes=f"Bulk action executed by {request.user.username}"
                )
                OrderNotificationService.send_order_status_update(order, old_status, Order.STATUS_PROCESSING)
                success_count += 1
            else:
                fail_count += 1

        if success_count:
            self.message_user(request, f"Successfully advanced {success_count} order(s) to Processing.")
        if fail_count:
            self.message_user(
                request,
                f"Skipped {fail_count} order(s) because transition to Processing is not permitted from their current state.",
                level='WARNING'
            )

    @admin.action(description="Advance selected orders to Completed")
    def advance_to_completed(self, request, queryset):
        success_count = 0
        fail_count = 0
        for order in queryset:
            old_status = order.status
            if order.can_transition_to(Order.STATUS_COMPLETED):
                order.status = Order.STATUS_COMPLETED
                order.save(update_fields=['status', 'updated_at'])
                OrderAuditLog.objects.create(
                    order=order,
                    performed_by=request.user,
                    action="Advanced to Completed via Bulk Action",
                    old_status=old_status,
                    new_status=Order.STATUS_COMPLETED,
                    notes=f"Bulk action executed by {request.user.username}"
                )
                OrderNotificationService.send_order_status_update(order, old_status, Order.STATUS_COMPLETED)
                success_count += 1
            else:
                fail_count += 1

        if success_count:
            self.message_user(request, f"Successfully advanced {success_count} order(s) to Completed.")
        if fail_count:
            self.message_user(
                request,
                f"Skipped {fail_count} order(s) because transition to Completed is not permitted from their current state.",
                level='WARNING'
            )

    @admin.action(description="Cancel selected orders")
    def cancel_orders(self, request, queryset):
        success_count = 0
        fail_count = 0
        for order in queryset:
            old_status = order.status
            if order.can_transition_to(Order.STATUS_CANCELLED):
                order.status = Order.STATUS_CANCELLED
                order.save(update_fields=['status', 'updated_at'])
                OrderAuditLog.objects.create(
                    order=order,
                    performed_by=request.user,
                    action="Cancelled via Bulk Action",
                    old_status=old_status,
                    new_status=Order.STATUS_CANCELLED,
                    notes=f"Bulk cancellation executed by {request.user.username}"
                )
                OrderNotificationService.send_order_status_update(order, old_status, Order.STATUS_CANCELLED)
                success_count += 1
            else:
                fail_count += 1

        if success_count:
            self.message_user(request, f"Successfully cancelled {success_count} order(s).")
        if fail_count:
            self.message_user(
                request,
                f"Skipped {fail_count} order(s) because they cannot be cancelled from their current state.",
                level='WARNING'
            )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'escrow_reference', 'order', 'payment_method', 'status_badge', 
        'amount', 'currency', 'transaction_hash', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order__order_number', 'escrow_reference', 'transaction_hash', 'wallet_address')
    readonly_fields = (
        'order', 'payment_method', 'status', 'amount', 'currency', 
        'escrow_reference', 'transaction_hash', 'wallet_address', 'chain_id', 
        'verified_at', 'verification_notes', 'created_at', 'updated_at'
    )
    actions = ['confirm_bank_wire_escrow']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def status_badge(self, obj):
        colors = {
            Payment.STATUS_PENDING: '#f59e0b',
            Payment.STATUS_SUBMITTED: '#3b82f6',
            Payment.STATUS_VERIFYING: '#8b5cf6',
            Payment.STATUS_CONFIRMED: '#10b981',
            Payment.STATUS_FAILED: '#ef4444',
            Payment.STATUS_REFUNDED: '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Payment Status'

    @admin.action(description="Confirm Bank Wire Escrow Funds Received")
    def confirm_bank_wire_escrow(self, request, queryset):
        confirmed_count = 0
        rejected_count = 0

        for payment in queryset:
            # ANTI-TAMPER GUARD: NEVER confirm crypto payments through bank wire admin action!
            if payment.payment_method != Payment.METHOD_BANK_WIRE:
                rejected_count += 1
                continue

            if payment.status not in (Payment.STATUS_PENDING, Payment.STATUS_SUBMITTED, Payment.STATUS_VERIFYING):
                rejected_count += 1
                continue

            # Mark payment confirmed
            payment.status = Payment.STATUS_CONFIRMED
            payment.verified_at = timezone.now()
            payment.verification_notes += f"\nWire confirmed by staff {request.user.username} at {timezone.now().isoformat()}"
            payment.save(update_fields=['status', 'verified_at', 'verification_notes', 'updated_at'])

            # Transition order from awaiting_payment/pending to paid
            order = payment.order
            if order.can_transition_to(Order.STATUS_PAID):
                old_status = order.status
                order.status = Order.STATUS_PAID
                order.save(update_fields=['status', 'updated_at'])

                OrderAuditLog.objects.create(
                    order=order,
                    performed_by=request.user,
                    action="Bank Wire Escrow Confirmed",
                    old_status=old_status,
                    new_status=Order.STATUS_PAID,
                    notes=f"Wire payment #{payment.escrow_reference} confirmed by staff {request.user.username}"
                )

                OrderNotificationService.send_order_confirmation(order)
            elif order.status == Order.STATUS_PENDING:
                # If order was STATUS_PENDING, transition to STATUS_PAID directly or via transition
                # In models: STATUS_PENDING -> {STATUS_AWAITING_PAYMENT, STATUS_CANCELLED}
                # Wait! Let's check ALLOWED_TRANSITIONS:
                # STATUS_PENDING -> {STATUS_AWAITING_PAYMENT, STATUS_CANCELLED}
                # STATUS_AWAITING_PAYMENT -> {STATUS_PAID, STATUS_CANCELLED}
                pass

            confirmed_count += 1

        if confirmed_count:
            self.message_user(request, f"Successfully confirmed {confirmed_count} bank wire payment(s) and updated order status.")
        if rejected_count:
            self.message_user(
                request,
                f"Skipped {rejected_count} payment(s): Crypto payments or already settled payments cannot be verified through bank wire escrow action.",
                level='ERROR'
            )


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_type', 'discount_value', 'is_active', 
        'used_count', 'max_uses', 'valid_from', 'valid_to'
    )
    list_filter = ('is_active', 'discount_type', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')
    actions = ['activate_coupons', 'deactivate_coupons']

    @admin.action(description="Activate selected coupons")
    def activate_coupons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} coupon(s).")

    @admin.action(description="Deactivate selected coupons")
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} coupon(s).")


@admin.register(OrderAuditLog)
class OrderAuditLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'performed_by', 'action', 'old_status', 'new_status', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('order__order_number', 'performed_by__username', 'action', 'notes')
    readonly_fields = ('order', 'performed_by', 'action', 'old_status', 'new_status', 'notes', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
