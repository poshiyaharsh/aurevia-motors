import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('apps.orders')


class OrderNotificationService:
    """
    Concierge notification service for Aurevia Motors acquisition orders.
    Enforces safe SMTP delivery: catches any connection/delivery errors without corrupting
    order data or aborting database transactions.
    """

    @classmethod
    def is_email_configured(cls) -> bool:
        """
        Checks whether email delivery is configured in settings.
        """
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        host = getattr(settings, 'EMAIL_HOST', '')
        return bool(backend or host)

    @classmethod
    def send_order_placed_notification(cls, order) -> tuple[bool, str]:
        """
        Sends an acquisition reservation notification when an order is created.
        """
        recipient = order.user.email
        if not recipient:
            return False, "User has no email address configured."

        subject = f"[Aurevia Motors] Order Registered — {order.order_number}"
        context = {
            'order': order,
            'payment': getattr(order, 'payment', None),
            'items': order.items.all(),
        }

        body_lines = [
            f"Dear {order.shipping_full_name or order.user.username},",
            "",
            f"Your luxury vehicle acquisition order {order.order_number} has been officially recorded.",
            f"Settlement Valuation: {order.currency} ${order.grand_total:,.2f}",
            f"Settlement Rail: {order.payment.get_payment_method_display() if hasattr(order, 'payment') else 'Escrow'}",
            f"Escrow Identifier: {order.payment.escrow_reference if hasattr(order, 'payment') else 'N/A'}",
            "",
            "Allocated Supercars:",
        ]
        for item in order.items.all():
            body_lines.append(f"  • {item.quantity}x {item.vehicle_year} {item.vehicle_brand_name} {item.vehicle_model_name} — {order.currency} ${item.line_total:,.2f}")

        body_lines.extend([
            "",
            f"Delivery Domicile: {order.shipping_address_line_1}, {order.shipping_city}, {order.shipping_country}",
            "",
            "Our Private Client Concierge is standing by to assist with title transfer and white-glove transport logistics.",
            "",
            "Aurevia Motors Atelier Concierge",
            "concierge@aureviamotors.com",
        ])
        plain_message = "\n".join(body_lines)

        return cls._safe_send_mail(
            subject=subject,
            message=plain_message,
            recipient_list=[recipient]
        )

    @classmethod
    def send_payment_confirmed_notification(cls, order) -> tuple[bool, str]:
        """
        Sends a payment cleared & confirmed notification to the customer.
        """
        recipient = order.user.email
        if not recipient:
            return False, "User has no email address configured."

        subject = f"[Aurevia Motors] Payment Cleared & Confirmed — Order {order.order_number}"
        body_lines = [
            f"Dear {order.shipping_full_name or order.user.username},",
            "",
            f"We are pleased to confirm that settlement for Order {order.order_number} has successfully cleared.",
            f"Verified Amount: {order.currency} ${order.grand_total:,.2f}",
            f"Current Order Status: {order.get_status_display()}",
            "",
            "Next Steps:",
            "  1. Pre-delivery manufacturer provenance documents are being finalized.",
            "  2. Enclosed climate-controlled transport is being coordinated to your delivery domicile.",
            "",
            "You may track your acquisition directly from your Atelier profile dashboard.",
            "",
            "Aurevia Motors Atelier Concierge",
        ]
        plain_message = "\n".join(body_lines)

        return cls._safe_send_mail(
            subject=subject,
            message=plain_message,
            recipient_list=[recipient]
        )

    # Method alias for convenience
    send_order_confirmation = send_payment_confirmed_notification

    @classmethod
    def send_order_status_notification(cls, order, old_status: str, new_status: str) -> tuple[bool, str]:
        """
        Sends an order lifecycle status transition notification.
        """
        recipient = order.user.email
        if not recipient:
            return False, "User has no email address configured."

        subject = f"[Aurevia Motors] Status Update: {order.get_status_display()} — {order.order_number}"
        body_lines = [
            f"Dear {order.shipping_full_name or order.user.username},",
            "",
            f"The status of your acquisition order {order.order_number} has progressed.",
            f"Previous Status: {old_status}",
            f"New Status: {order.get_status_display()}",
            "",
            "Our concierge remains at your disposal for any transport or title queries.",
            "",
            "Aurevia Motors Atelier Concierge",
        ]
        plain_message = "\n".join(body_lines)

        return cls._safe_send_mail(
            subject=subject,
            message=plain_message,
            recipient_list=[recipient]
        )

    # Method alias for convenience
    send_order_status_update = send_order_status_notification

    @classmethod
    def _safe_send_mail(cls, subject: str, message: str, recipient_list: list[str]) -> tuple[bool, str]:
        """
        Internal safe mail dispatcher.
        Catches all delivery exceptions, logs them defensively, and prevents order corruption.
        """
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'concierge@aureviamotors.com')

        try:
            sent_count = send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False
            )
            return True, f"Successfully dispatched {sent_count} notification email(s)."
        except Exception as e:
            logger.warning(
                f"SMTP/Email dispatch failed for recipient {recipient_list} (Subject: '{subject}'): {str(e)}. "
                "Order processing integrity maintained."
            )
            return False, f"Email dispatch failed: {str(e)}"
