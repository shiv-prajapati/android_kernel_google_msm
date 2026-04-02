import csv
import io
import os
from collections import defaultdict
from datetime import date, datetime

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AdSpend, Cogs, OrderItem


LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


class SPAPIClient:
    def __init__(self):
        self.client_id = os.getenv("SP_API_CLIENT_ID", "")
        self.client_secret = os.getenv("SP_API_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("SP_API_REFRESH_TOKEN", "")
        self.base_url = os.getenv("SP_API_REGION_BASE_URL", "https://sellingpartnerapi-na.amazon.com")

    def get_access_token(self) -> str:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = requests.post(LWA_TOKEN_URL, data=payload, timeout=30)
        response.raise_for_status()
        return response.json()["access_token"]

    def fetch_orders(self, start_date: date, end_date: date):
        """Fetches orders from SP-API Orders v0 and returns a normalized list.

        Note: This keeps request shape simple for an MVP and should be expanded
        for pagination, retries, and complete item-level enrichment.
        """
        token = self.get_access_token()
        url = f"{self.base_url}/orders/v0/orders"
        params = {
            "MarketplaceIds": "ATVPDKIKX0DER",  # US marketplace default
            "CreatedAfter": f"{start_date.isoformat()}T00:00:00Z",
            "CreatedBefore": f"{end_date.isoformat()}T23:59:59Z",
        }
        headers = {"x-amz-access-token": token}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        payload = response.json().get("payload", {})
        orders = payload.get("Orders", [])

        normalized = []
        for order in orders:
            # Placeholder item expansion: exact order item endpoint call omitted in MVP
            normalized.append(
                {
                    "order_id": order.get("AmazonOrderId", ""),
                    "purchase_date": order.get("PurchaseDate", "")[:10],
                    "sku": order.get("SellerOrderId", "UNKNOWN-SKU"),
                    "asin": "UNKNOWN-ASIN",
                    "quantity": 1,
                    "item_price": 0.0,
                    "amazon_fee": 0.0,
                }
            )
        return normalized


def upsert_cogs(db: Session, sku: str, unit_cogs: float):
    existing = db.execute(select(Cogs).where(Cogs.sku == sku)).scalar_one_or_none()
    if existing:
        existing.unit_cogs = unit_cogs
    else:
        db.add(Cogs(sku=sku, unit_cogs=unit_cogs))
    db.commit()


def store_orders(db: Session, orders: list[dict]):
    inserted = 0
    for row in orders:
        existing = db.execute(
            select(OrderItem).where(
                OrderItem.order_id == row["order_id"],
                OrderItem.sku == row["sku"],
                OrderItem.purchase_date == row["purchase_date"],
            )
        ).scalar_one_or_none()
        if existing:
            continue

        db.add(
            OrderItem(
                order_id=row["order_id"],
                purchase_date=datetime.strptime(row["purchase_date"], "%Y-%m-%d").date(),
                sku=row["sku"],
                asin=row["asin"],
                quantity=int(row["quantity"]),
                item_price=float(row["item_price"]),
                amazon_fee=float(row.get("amazon_fee", 0.0)),
            )
        )
        inserted += 1
    db.commit()
    return inserted


def import_ads_csv(db: Session, content: bytes):
    """CSV format: date,sku,amount"""
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    rows = 0
    for r in reader:
        db.add(AdSpend(spend_date=datetime.strptime(r["date"], "%Y-%m-%d").date(), sku=r["sku"], amount=float(r["amount"])))
        rows += 1
    db.commit()
    return rows


def pnl_report(db: Session, start_date: date, end_date: date):
    order_rows = db.execute(
        select(
            OrderItem.sku,
            func.sum(OrderItem.quantity).label("units"),
            func.sum(OrderItem.item_price).label("revenue"),
            func.sum(OrderItem.amazon_fee).label("fees"),
        ).where(OrderItem.purchase_date.between(start_date, end_date)).group_by(OrderItem.sku)
    ).all()

    ad_rows = db.execute(
        select(AdSpend.sku, func.sum(AdSpend.amount).label("ad_spend"))
        .where(AdSpend.spend_date.between(start_date, end_date))
        .group_by(AdSpend.sku)
    ).all()
    ad_by_sku = {r[0]: float(r[1] or 0.0) for r in ad_rows}

    cogs_rows = db.execute(select(Cogs.sku, Cogs.unit_cogs)).all()
    cogs_by_sku = {r[0]: float(r[1]) for r in cogs_rows}

    report = []
    for sku, units, revenue, fees in order_rows:
        units = int(units or 0)
        revenue = float(revenue or 0.0)
        fees = float(fees or 0.0)
        ad_spend = ad_by_sku.get(sku, 0.0)
        cogs = cogs_by_sku.get(sku, 0.0) * units
        net_profit = revenue - fees - ad_spend - cogs
        margin_pct = (net_profit / revenue * 100.0) if revenue else 0.0

        report.append(
            {
                "sku": sku,
                "units": units,
                "revenue": round(revenue, 2),
                "amazon_fees": round(fees, 2),
                "ad_spend": round(ad_spend, 2),
                "cogs": round(cogs, 2),
                "net_profit": round(net_profit, 2),
                "margin_pct": round(margin_pct, 2),
            }
        )

    report.sort(key=lambda x: x["net_profit"], reverse=True)
    return report
