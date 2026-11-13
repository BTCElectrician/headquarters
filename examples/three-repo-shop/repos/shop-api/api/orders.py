"""Orders for the example shop API."""

import itertools

_ids = itertools.count(1)
_orders = {}


def create_order(email, items, total):
    """Create an order and return it. Called by shop-app at checkout."""
    if not items:
        raise ValueError("an order needs at least one item")
    order = {"id": next(_ids), "email": email, "items": items, "total": total}
    _orders[order["id"]] = order
    return order


def get_order(order_id):
    """Return one order by id, or None."""
    return _orders.get(order_id)
