from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, CustomerProfileForm, AddressForm
from .models import Address, CustomerProfile


def register_view(request):
    """
    Onboards new clientele to Aurevia Motors Atelier.
    """
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Aurevia Motors, {user.first_name or user.username}. Your client atelier portal is ready.")
            return redirect('accounts:profile')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Client authentication gateway.
    """
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    redirect_to = request.GET.get('next', 'accounts:profile')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}.")
            return redirect(redirect_to)
        else:
            messages.error(request, "Invalid credentials. Please verify your username and confidential password.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': redirect_to})


def logout_view(request):
    """
    Terminates client session safely.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been securely signed out of your client session.")
    return redirect('core:home')


@login_required
def profile_view(request):
    """
    Private client atelier dashboard displaying profile settings and address book.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    addresses = request.user.addresses.all()

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your client profile and preferences have been updated.")
            return redirect('accounts:profile')
    else:
        form = CustomerProfileForm(instance=profile, user=request.user)

    context = {
        'profile': profile,
        'form': form,
        'addresses': addresses,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def address_create_view(request):
    """
    Registers a new delivery or billing address for the client.
    """
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address successfully registered in your atelier address book.")
            return redirect('accounts:profile')
    else:
        form = AddressForm()

    return render(request, 'accounts/address_form.html', {'form': form, 'title': 'Add New Destination Address'})


@login_required
def address_edit_view(request, pk):
    """
    Updates an existing address with strict ownership validation.
    """
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address details updated successfully.")
            return redirect('accounts:profile')
    else:
        form = AddressForm(instance=address)

    return render(request, 'accounts/address_form.html', {'form': form, 'title': 'Edit Destination Address', 'address': address})


@login_required
def address_delete_view(request, pk):
    """
    Removes an address with strict ownership validation.
    """
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address removed from your atelier address book.")
        return redirect('accounts:profile')

    return render(request, 'accounts/address_confirm_delete.html', {'address': address})
