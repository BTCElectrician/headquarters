import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.orders import create_order, get_order  # noqa: E402


class OrdersTest(unittest.TestCase):
    def test_create_order_then_get_order(self):
        order = create_order("a@example.com", [{"sku": "mug"}], 12)
        self.assertEqual(get_order(order["id"]), order)

    def test_create_order_needs_items(self):
        with self.assertRaises(ValueError):
            create_order("a@example.com", [], 0)


if __name__ == "__main__":
    unittest.main()
