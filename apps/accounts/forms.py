from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomerProfile, Address

User = get_user_model()


class CustomerRegistrationForm(UserCreationForm):
    """
    Client registration form with required unique email and legal name.
    """
    first_name = forms.CharField(max_length=50, required=True, label="First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Confidential Email")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address is already registered.")
        return email


class CustomerProfileForm(forms.ModelForm):
    """
    Form to update collector profile attributes.
    """
    first_name = forms.CharField(max_length=50, required=False, label="First Name")
    last_name = forms.CharField(max_length=50, required=False, label="Last Name")
    email = forms.EmailField(required=True, label="Primary Email")

    class Meta:
        model = CustomerProfile
        fields = (
            'phone_number',
            'preferred_currency',
            'preferred_contact_method',
            'collector_preferences'
        )
        labels = {
            'phone_number': 'Direct Concierge Phone',
            'preferred_currency': 'Preferred Valuation Currency',
            'preferred_contact_method': 'Preferred Contact Channel',
            'collector_preferences': 'Collector Portfolio Interests & Bespoke Preferences',
        }
        widgets = {
            'collector_preferences': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if self.user and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError("Another client account is already associated with this email.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name')
            self.user.last_name = self.cleaned_data.get('last_name')
            self.user.email = self.cleaned_data.get('email')
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


class AddressForm(forms.ModelForm):
    """
    Destination address validation form.
    """
    class Meta:
        model = Address
        fields = (
            'address_type',
            'full_name',
            'street_line_1',
            'street_line_2',
            'city',
            'state_or_province',
            'postal_code',
            'country',
            'is_default',
        )
        labels = {
            'address_type': 'Address Classification',
            'full_name': 'Recipient / Entity Legal Name',
            'street_line_1': 'Street Address',
            'street_line_2': 'Suite / Estate / Hangar (Optional)',
            'city': 'City / Municipality',
            'state_or_province': 'State / Province / Region',
            'postal_code': 'Postal / ZIP Code',
            'country': 'Country',
            'is_default': 'Set as Default Address for this category',
        }
