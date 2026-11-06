from .cart import Cart


def cart_context(request):
    """
    Exposes the active Cart instance to all templates globally.
    Defensively handles requests without session middleware.
    """
    return {
        'cart': Cart(request),
    }
