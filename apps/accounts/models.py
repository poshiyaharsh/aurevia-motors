from django.db import models
from django.conf import settings


class CustomerProfile(models.Model):
    """
    Extended profile for authenticated Aurevia Motors clientele.
    """
    CONTACT_EMAIL = 'email'
    CONTACT_PHONE = 'phone'
    CONTACT_PORTAL = 'secure_portal'

    CONTACT_CHOICES = [
        (CONTACT_EMAIL, 'Confidential Email'),
        (CONTACT_PHONE, 'Direct Phone Concierge'),
        (CONTACT_PORTAL, 'Secure Client Portal'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Underlying user account"
    )
    phone_number = models.CharField(max_length=30, blank=True, help_text="Direct concierge contact number")
    preferred_currency = models.CharField(max_length=3, default='USD', help_text="Default valuation currency")
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=CONTACT_CHOICES,
        default=CONTACT_EMAIL,
        help_text="Preferred confidential communication channel"
    )
    collector_preferences = models.TextField(
        blank=True,
        help_text="Specific marque interests, bespoke options, and vehicle requirements"
    )
    is_verified_collector = models.BooleanField(
        default=False,
        help_text="Mark if client has undergone provenance & KYC verification"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'

    def __str__(self):
        return f"Profile for {self.user.username}"


class Address(models.Model):
    """
    Delivery and billing destination addresses managed by the client.
    """
    TYPE_SHIPPING = 'shipping'
    TYPE_BILLING = 'billing'

    ADDRESS_TYPE_CHOICES = [
        (TYPE_SHIPPING, 'Vehicle Enclosed Delivery Destination'),
        (TYPE_BILLING, 'Billing Destination'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        help_text="Account owner of this address"
    )
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default=TYPE_SHIPPING,
        help_text="Classification of address"
    )
    full_name = models.CharField(max_length=120, help_text="Full legal name or corporate entity")
    street_line_1 = models.CharField(max_length=200, help_text="Street address")
    street_line_2 = models.CharField(max_length=200, blank=True, help_text="Suite, Estate, Hangar, or Unit")
    city = models.CharField(max_length=100)
    state_or_province = models.CharField(max_length=100, help_text="State, County, or Province")
    postal_code = models.CharField(max_length=30, help_text="Postal / ZIP code")
    country = models.CharField(max_length=100, help_text="Country destination")
    is_default = models.BooleanField(default=False, help_text="Primary address for this category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f"{self.full_name} — {self.city}, {self.country} ({self.get_address_type_display()})"

    def save(self, *args, **kwargs):
        # If this address is set as default, reset other addresses of the same type for this user
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
