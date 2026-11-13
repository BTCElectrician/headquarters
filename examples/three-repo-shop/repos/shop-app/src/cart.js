// Cart and checkout for the example storefront.

function cartTotal(items) {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

async function checkout(items, email, createOrder) {
  if (items.length === 0) {
    throw new Error("cart is empty");
  }
  // createOrder calls shop-api: POST /orders
  return createOrder({ email, items, total: cartTotal(items) });
}

module.exports = { cartTotal, checkout };
