from __future__ import annotations

import random
from datetime import date

from scripts.generate_orders import make_order


def test_generated_orders_are_synthetic_and_deterministic() -> None:
    a = make_order(7, random.Random(1), date(2026, 11, 30))
    b = make_order(7, random.Random(1), date(2026, 11, 30))
    assert a == b
    assert a["order_id"] == "SX-000007"
    assert a["email"].endswith("@example.com")
