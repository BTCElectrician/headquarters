const test = require("node:test");
const assert = require("node:assert");
const { cartTotal, checkout } = require("../src/cart.js");

test("cart total adds price times quantity", () => {
  assert.strictEqual(cartTotal([{ price: 5, quantity: 2 }, { price: 1, quantity: 3 }]), 13);
});

test("checkout refuses an empty cart", async () => {
  await assert.rejects(checkout([], "a@example.com", async () => ({})));
});
