from django.contrib import admin
from .models import CustomerProfile, Address


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'preferred_currency', 'preferred_contact_method', 'is_verified_collector', 'created_at']
    list_filter = ['is_verified_collector', 'preferred_currency', 'preferred_contact_method']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['verify_collector_status', 'revoke_collector_status']

    @admin.action(description="Verify selected collectors (grant VIP status)")
    def verify_collector_status(self, request, queryset):
        updated = queryset.update(is_verified_collector=True)
        self.message_user(request, f"Granted VIP collector status to {updated} profile(s).")

    @admin.action(description="Revoke VIP collector status")
    def revoke_collector_status(self, request, queryset):
        updated = queryset.update(is_verified_collector=False)
        self.message_user(request, f"Revoked VIP collector status from {updated} profile(s).")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'address_type', 'city', 'country', 'is_default', 'created_at']
    list_filter = ['address_type', 'is_default', 'country']
    search_fields = ['full_name', 'user__username', 'user__email', 'city', 'postal_code', 'street_line_1']
    readonly_fields = ['created_at', 'updated_at']
