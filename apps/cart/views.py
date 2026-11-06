from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.catalog.models import Vehicle
from .cart import Cart


def cart_detail_view(request):
    """
    Renders the current atelier cart summary with line items and recalculations.
    """
    cart = Cart(request)
    context = {
        'cart': cart,
        'cart_total': cart.get_total_price(),
    }
    return render(request, 'cart/cart_detail.html', context)


@require_POST
def cart_add_view(request, vehicle_id):
    """
    Adds an available vehicle to the client's atelier cart.
    """
    cart = Cart(request)
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    quantity = request.POST.get('quantity', 1)

    try:
        cart.add(vehicle=vehicle, quantity=quantity)
        messages.success(request, f"Added {vehicle.year} {vehicle.brand.name} {vehicle.model_name} to your atelier cart.")
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('catalog:vehicle_detail', slug=vehicle.slug)

    return redirect('cart:cart_detail')


@require_POST
def cart_update_view(request, vehicle_id):
    """
    Updates the quantity of a vehicle in the cart.
    """
    cart = Cart(request)
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    quantity = request.POST.get('quantity', 1)

    cart.update(vehicle=vehicle, quantity=quantity)
    messages.info(request, f"Updated reservation allocation for {vehicle.model_name}.")
    return redirect('cart:cart_detail')


def cart_remove_view(request, vehicle_id):
    """
    Removes a vehicle allocation from the cart.
    """
    cart = Cart(request)
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    cart.remove(vehicle=vehicle)
    messages.info(request, f"Removed {vehicle.model_name} from your atelier cart.")
    return redirect('cart:cart_detail')


def cart_clear_view(request):
    """
    Clears all allocations from the atelier cart.
    """
    cart = Cart(request)
    cart.clear()
    messages.info(request, "Your atelier cart has been cleared.")
    return redirect('cart:cart_detail')
