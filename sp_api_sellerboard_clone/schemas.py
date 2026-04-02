from datetime import date

from pydantic import BaseModel, Field


class CogsUpsert(BaseModel):
    sku: str = Field(min_length=1)
    unit_cogs: float = Field(ge=0)


class SyncOrdersRequest(BaseModel):
    start_date: date
    end_date: date


class PnlRow(BaseModel):
    sku: str
    units: int
    revenue: float
    amazon_fees: float
    ad_spend: float
    cogs: float
    net_profit: float
    margin_pct: float
