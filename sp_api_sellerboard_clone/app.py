import os
from contextlib import contextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from .models import build_session_factory
from .schemas import CogsUpsert, PnlRow, SyncOrdersRequest
from .services import SPAPIClient, import_ads_csv, pnl_report, store_orders, upsert_cogs

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sp_board.db")
SessionLocal = build_session_factory(DATABASE_URL)
sp_client = SPAPIClient()

app = FastAPI(title="SP-Board API", version="0.1.0")


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/cogs")
def set_cogs(payload: CogsUpsert):
    with db_session() as db:
        upsert_cogs(db, payload.sku, payload.unit_cogs)
    return {"status": "saved", "sku": payload.sku}


@app.post("/sync/orders")
def sync_orders(payload: SyncOrdersRequest):
    orders = sp_client.fetch_orders(payload.start_date, payload.end_date)
    with db_session() as db:
        inserted = store_orders(db, orders)
    return {"fetched": len(orders), "inserted": inserted}


@app.post("/sync/ads/csv")
def sync_ads_csv(file: UploadFile = File(...)):
    content = file.file.read()
    with db_session() as db:
        rows = import_ads_csv(db, content)
    return {"rows_imported": rows}


@app.get("/reports/pnl", response_model=list[PnlRow])
def get_pnl_report(start_date: date, end_date: date):
    with db_session() as db:
        report = pnl_report(db, start_date, end_date)
    return JSONResponse(content=report)
