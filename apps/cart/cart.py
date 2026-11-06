from decimal import Decimal
from django.conf import settings
from apps.catalog.models import Vehicle

CART_SESSION_ID = getattr(settings, 'CART_SESSION_ID', 'aurevia_atelier_cart')
MAX_ALLOCATION_PER_VEHICLE = 5


class Cart:
    """
    Session-backed Cart management service with strict server-side price recalculation.
    """
    def __init__(self, request):
        if hasattr(request, 'session'):
            self.session = request.session
            cart = self.session.get(CART_SESSION_ID)
            if not cart:
                cart = self.session[CART_SESSION_ID] = {}
            self.cart = cart
        else:
            self.session = {}
            self.cart = {}

    def add(self, vehicle, quantity=1, override_quantity=False):
        """
        Adds an available vehicle to the cart or updates quantity.
        Enforces availability check and bounds quantity between 1 and MAX_ALLOCATION_PER_VEHICLE.
        """
        if vehicle.status != Vehicle.STATUS_AVAILABLE:
            raise ValueError(f"Vehicle '{vehicle}' is currently {vehicle.get_status_display()} and cannot be added to cart.")

        vehicle_id = str(vehicle.id)

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 1

        if quantity < 1:
            quantity = 1

        if vehicle_id not in self.cart:
            # We store only the vehicle id and quantity in session.
            # Price is NEVER trusted from session/client and is always fetched live from DB.
            self.cart[vehicle_id] = {'quantity': 0}

        if override_quantity:
            new_quantity = quantity
        else:
            new_quantity = self.cart[vehicle_id]['quantity'] + quantity

        # Clamp quantity to maximum allocation limit
        self.cart[vehicle_id]['quantity'] = min(new_quantity, MAX_ALLOCATION_PER_VEHICLE)
        self.save()

    def update(self, vehicle, quantity):
        """
        Updates quantity for an existing cart item. If quantity <= 0, removes item.
        """
        vehicle_id = str(vehicle.id)
        if vehicle_id in self.cart:
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 1

            if quantity <= 0:
                self.remove(vehicle)
            else:
                self.cart[vehicle_id]['quantity'] = min(quantity, MAX_ALLOCATION_PER_VEHICLE)
                self.save()

    def remove(self, vehicle):
        """
        Removes a vehicle from the cart.
        """
        vehicle_id = str(vehicle.id)
        if vehicle_id in self.cart:
            del self.cart[vehicle_id]
            self.save()

    def clear(self):
        """
        Empties the cart.
        """
        if hasattr(self.session, '__setitem__'):
            self.session[CART_SESSION_ID] = {}
            self.cart = self.session[CART_SESSION_ID]
            self.save()
        else:
            self.cart = {}

    def save(self):
        """
        Marks session as modified to ensure it is stored.
        """
        if hasattr(self.session, 'modified'):
            self.session.modified = True

    def __iter__(self):
        """
        Iterates over the items in the cart, querying authoritative live
        vehicle objects, prices, and media from the database.
        """
        vehicle_ids = self.cart.keys()
        vehicles = Vehicle.objects.filter(id__in=vehicle_ids).select_related('brand')
        cart_copy = {k: v.copy() for k, v in self.cart.items()}

        for vehicle in vehicles:
            cart_copy[str(vehicle.id)]['vehicle'] = vehicle
            # Server-side authoritative price
            cart_copy[str(vehicle.id)]['price'] = vehicle.price
            cart_copy[str(vehicle.id)]['currency'] = vehicle.currency
            cart_copy[str(vehicle.id)]['total_price'] = vehicle.price * cart_copy[str(vehicle.id)]['quantity']

        for item in cart_copy.values():
            if 'vehicle' in item:
                yield item

    def __len__(self):
        """
        Counts total number of units in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Calculates the grand total price strictly from database prices.
        """
        vehicle_ids = self.cart.keys()
        vehicles = {str(v.id): v for v in Vehicle.objects.filter(id__in=vehicle_ids)}
        total = Decimal('0.00')

        for v_id, item in self.cart.items():
            if v_id in vehicles:
                total += vehicles[v_id].price * item['quantity']

        return total

    @property
    def is_empty(self):
        return len(self.cart) == 0
