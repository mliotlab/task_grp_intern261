"""Generate synthetic ShopX orders for the mock Order API.

No real personal data: every email uses the reserved example.com domain.

    python scripts/generate_orders.py --n 100 --seed 42 --out var/orders.json
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

PRODUCTS = [
    "Wireless Earbuds X1", "Smart Watch S2", "USB-C Charger 65W", "Mechanical Keyboard K8",
    "Gaming Mouse M3", "Laptop Stand", "Phone Case Pro", "Bluetooth Speaker Mini",
    "Power Bank 20000mAh", "4K Webcam", "Desk Lamp LED", "Backpack Urban 20L",
]  # fmt: skip
CARRIERS = ["GHN", "GHTK", "Viettel Post", "J&T Express"]
STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled", "returned"]
WEIGHTS = [0.10, 0.15, 0.30, 0.35, 0.05, 0.05]


def make_order(i: int, rng: random.Random, today: date) -> dict:
    placed = today - timedelta(days=rng.randint(0, 60))
    status = rng.choices(STATUSES, WEIGHTS)[0]
    items = rng.sample(PRODUCTS, k=rng.randint(1, 3))
    shipped = status in {"shipped", "delivered", "returned"}
    return {
        "order_id": f"SX-{i:06d}",
        "email": f"customer{i:03d}@example.com",
        "status": status,
        "items": items,
        "total_vnd": rng.randint(5, 300) * 10_000,
        "placed_on": placed.isoformat(),
        "estimated_delivery": (placed + timedelta(days=rng.randint(2, 7))).isoformat()
        if status not in {"cancelled"}
        else None,
        "carrier": rng.choice(CARRIERS) if shipped else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--today", type=date.fromisoformat, default=date(2026, 11, 30))
    parser.add_argument("--out", type=Path, default=Path("var/orders.json"))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    orders = [make_order(i, rng, args.today) for i in range(1, args.n + 1)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(orders, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(orders)} orders to {args.out}")


if __name__ == "__main__":
    main()
