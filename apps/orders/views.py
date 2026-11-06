from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import Address
from apps.catalog.models import Vehicle
from apps.cart.cart import Cart
from .models import Order, OrderItem, Payment, Coupon
from .pricing import PricingEngine
from .payments import PaymentVerificationService


@login_required
def checkout_view(request):
    """
    Renders the checkout review screen.
    Displays saved customer addresses, payment methods, and server-authoritative totals.
    """
    cart = Cart(request)
    if cart.is_empty:
        messages.info(request, "Your atelier cart is empty. Please select a vehicle from our curated collection.")
        return redirect('catalog:vehicle_list')

    calculation = PricingEngine.calculate_cart(cart, coupon_code=cart.coupon_code)
    user_addresses = Address.objects.filter(user=request.user)
    default_address = user_addresses.filter(is_default=True).first() or user_addresses.first()

    context = {
        'cart': cart,
        'calculation': calculation,
        'user_addresses': user_addresses,
        'default_address': default_address,
        'payment_methods': Payment.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
@require_POST
def checkout_process_view(request):
    """
    Processes the checkout submission.
    Atomically creates the Order, frozen line items, and Payment record,
    then clears the atelier cart.
    """
    cart = Cart(request)
    if cart.is_empty:
        messages.error(request, "Your atelier cart is empty.")
        return redirect('catalog:vehicle_list')

    # Resolve delivery address with strict ownership validation
    address_id = request.POST.get('address_id')
    if address_id:
        address = get_object_or_404(Address, id=address_id, user=request.user)
        shipping_full_name = address.full_name
        profile = getattr(request.user, 'profile', None)
        shipping_phone = profile.phone_number if profile and profile.phone_number else ''
        shipping_address_line_1 = address.street_line_1
        shipping_address_line_2 = address.street_line_2 or ''
        shipping_city = address.city
        shipping_state_province = address.state_or_province
        shipping_postal_code = address.postal_code
        shipping_country = address.country
    else:
        # Inline address input validation
        shipping_full_name = request.POST.get('full_name', '').strip()
        shipping_phone = request.POST.get('phone', '').strip()
        shipping_address_line_1 = request.POST.get('address_line_1', '').strip()
        shipping_address_line_2 = request.POST.get('address_line_2', '').strip()
        shipping_city = request.POST.get('city', '').strip()
        shipping_state_province = request.POST.get('state_province', '').strip()
        shipping_postal_code = request.POST.get('postal_code', '').strip()
        shipping_country = request.POST.get('country', '').strip()

        if not all([shipping_full_name, shipping_phone, shipping_address_line_1, shipping_city, shipping_postal_code, shipping_country]):
            messages.error(request, "Please provide complete delivery and registration address details.")
            return redirect('orders:checkout')

    # Payment method choice
    payment_method = request.POST.get('payment_method', Payment.METHOD_BANK_WIRE)
    valid_methods = [choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES]
    if payment_method not in valid_methods:
        payment_method = Payment.METHOD_BANK_WIRE

    # Authoritative server pricing recalculation
    calculation = PricingEngine.calculate_cart(cart, coupon_code=cart.coupon_code)

    # Verify vehicle availability
    for item in cart:
        if item['vehicle'].status != Vehicle.STATUS_AVAILABLE:
            messages.error(
                request,
                f"Vehicle '{item['vehicle']}' is no longer available for reservation. Allocation removed."
            )
            return redirect('cart:cart_detail')

    client_notes = request.POST.get('client_notes', '').strip()

    with transaction.atomic():
        # Create authoritative Order
        order = Order.objects.create(
            user=request.user,
            status=Order.STATUS_AWAITING_PAYMENT,
            shipping_full_name=shipping_full_name,
            shipping_phone=shipping_phone,
            shipping_address_line_1=shipping_address_line_1,
            shipping_address_line_2=shipping_address_line_2,
            shipping_city=shipping_city,
            shipping_state_province=shipping_state_province,
            shipping_postal_code=shipping_postal_code,
            shipping_country=shipping_country,
            subtotal=calculation.subtotal,
            discount_amount=calculation.discount_amount,
            tax_amount=calculation.tax_amount,
            delivery_fee=calculation.delivery_fee,
            grand_total=calculation.grand_total,
            currency=calculation.currency,
            coupon=calculation.coupon,
            coupon_code_snapshot=calculation.coupon.code if calculation.coupon else '',
            client_notes=client_notes,
        )

        # Create immutable purchase-time snapshots for each order item
        for item in cart:
            v = item['vehicle']
            OrderItem.objects.create(
                order=order,
                vehicle=v,
                vehicle_model_name=v.model_name,
                vehicle_brand_name=v.brand.name,
                vehicle_year=v.year,
                vehicle_vin=v.vin or '',
                unit_price=v.price,
                quantity=item['quantity'],
                line_total=item['total_price'],
            )

        # Create associated Payment ledger entry
        Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=order.grand_total,
            currency=order.currency,
            status=Payment.STATUS_PENDING,
        )

        # Increment coupon usage if applied
        if calculation.coupon:
            calculation.coupon.used_count += 1
            calculation.coupon.save()

        # Clear session cart
        cart.clear()

    return redirect('orders:payment_detail', order_number=order.order_number)


@login_required
def payment_detail_view(request, order_number):
    """
    Renders the payment interface for a specific order.
    Enforces strict ownership access (404 for cross-user attempts).
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = order.payment

    context = {
        'order': order,
        'payment': payment,
        'rpc_configured': bool(PaymentVerificationService.get_rpc_url()),
        'settlement_address': PaymentVerificationService.get_settlement_address(),
    }
    return render(request, 'orders/payment.html', context)


@login_required
@require_POST
def payment_confirm_wire_view(request, order_number):
    """
    Client confirms bank wire initiation. Transitions payment status to SUBMITTED.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = order.payment

    payment.status = Payment.STATUS_SUBMITTED
    payment.verification_notes = f"Client confirmed wire transfer dispatch at {timezone.now().isoformat()}."
    payment.save()

    messages.success(
        request,
        f"Wire transfer submission recorded for order {order.order_number}. "
        f"Aurevia Concierge will verify receipt within 1 business day."
    )
    return redirect('orders:order_confirmation', order_number=order.order_number)


@login_required
@require_POST
def payment_verify_crypto_view(request, order_number):
    """
    Processes client-submitted EVM transaction hash for on-chain cryptographic verification.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = order.payment

    tx_hash = request.POST.get('tx_hash', '').strip()
    wallet_address = request.POST.get('wallet_address', '').strip()
    chain_id = request.POST.get('chain_id', '').strip()

    verified, reason = PaymentVerificationService.verify_crypto_payment(
        payment=payment,
        tx_hash=tx_hash,
        wallet_address=wallet_address,
        chain_id=chain_id
    )

    if verified:
        messages.success(request, f"Transaction cryptographically verified on-chain! Order {order.order_number} is PAID.")
        return redirect('orders:order_confirmation', order_number=order.order_number)
    else:
        messages.warning(request, reason)
        return redirect('orders:payment_detail', order_number=order.order_number)


@login_required
def order_confirmation_view(request, order_number):
    """
    Renders the order confirmation and receipt screen.
    Enforces strict customer ownership isolation.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    context = {
        'order': order,
        'payment': order.payment,
    }
    return render(request, 'orders/order_confirmation.html', context)
