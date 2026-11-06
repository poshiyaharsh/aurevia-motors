from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.catalog.models import Vehicle
from apps.orders.pricing import PricingEngine
from .cart import Cart


def cart_detail_view(request):
    """
    Renders the current atelier cart summary with line items and recalculations.
    """
    cart = Cart(request)
    calculation = PricingEngine.calculate_cart(cart, coupon_code=cart.coupon_code)

    # If a previously applied coupon became invalid (e.g. cart subtotal dropped below min order value)
    if cart.coupon_code and not calculation.is_coupon_applied:
        cart.clear_coupon()
        messages.warning(request, f"Applied coupon was removed: {calculation.coupon_rejection_reason}")
        calculation = PricingEngine.calculate_cart(cart, coupon_code=None)

    context = {
        'cart': cart,
        'calculation': calculation,
        'cart_total': calculation.grand_total,
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


@require_POST
def coupon_apply_view(request):
    """
    Validates and applies a promotional code / voucher to the current cart.
    Server strictly recalculates the subtotal and validates business rules.
    """
    cart = Cart(request)
    code = request.POST.get('code', '').strip()

    if not code:
        messages.error(request, "Please enter a promotional code or voucher.")
        return redirect('cart:cart_detail')

    if cart.is_empty:
        messages.error(request, "Cannot apply a voucher to an empty atelier cart.")
        return redirect('cart:cart_detail')

    calculation = PricingEngine.calculate_cart(cart, coupon_code=code)

    if calculation.is_coupon_applied:
        cart.set_coupon(calculation.coupon.code)
        messages.success(
            request,
            f"Voucher '{calculation.coupon.code}' applied. Concession of USD ${calculation.discount_amount:,.2f} applied."
        )
    else:
        messages.error(request, calculation.coupon_rejection_reason or "Unable to apply promotional code.")

    return redirect('cart:cart_detail')


@require_POST
def coupon_remove_view(request):
    """
    Removes any applied coupon from the atelier session.
    """
    cart = Cart(request)
    cart.clear_coupon()
    messages.info(request, "Promotional voucher removed from your order.")
    return redirect('cart:cart_detail')
