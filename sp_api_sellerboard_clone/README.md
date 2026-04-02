# SP-Board (Sellerboard-like starter for Amazon SP-API)

SP-Board is a starter analytics service that connects to Amazon's Selling Partner API (SP-API) and computes SKU-level profit metrics similar to Sellerboard:

- Revenue
- Units sold
- Amazon fees
- Ad spend (from imported ads file/API)
- COGS
- Estimated net profit
- Profit margin

> This is an MVP scaffold, not a complete production clone.

## Features

- FastAPI backend
- OAuth2 refresh-token flow for SP-API access token generation
- Orders ingestion from SP-API
- SQLite storage (easy local startup)
- SKU-level P&L report endpoint
- CSV import endpoint for ad spend by SKU/date

## Project structure

```
sp_api_sellerboard_clone/
├── app.py                # FastAPI app and API endpoints
├── models.py             # SQLite models via SQLAlchemy
├── services.py           # SP-API auth + ingestion + reporting logic
├── schemas.py            # Pydantic request/response models
├── requirements.txt
└── .env.example
```

## Quick start

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r sp_api_sellerboard_clone/requirements.txt
```

2. Configure environment:

```bash
cp sp_api_sellerboard_clone/.env.example .env
# fill values
```

3. Run API:

```bash
uvicorn sp_api_sellerboard_clone.app:app --reload --port 8080
```

## Required env vars

- `SP_API_CLIENT_ID`
- `SP_API_CLIENT_SECRET`
- `SP_API_REFRESH_TOKEN`
- `SP_API_REGION_BASE_URL` (example: `https://sellingpartnerapi-na.amazon.com`)
- `DATABASE_URL` (default: `sqlite:///./sp_board.db`)

## Example workflow

1. Set SKU-level COGS manually:
   - `POST /cogs`
2. Import orders for a date range:
   - `POST /sync/orders`
3. Import ad costs from CSV:
   - `POST /sync/ads/csv`
4. Get report:
   - `GET /reports/pnl?start_date=2026-01-01&end_date=2026-01-31`

## Notes

- Amazon SP-API rate limits apply.
- For production use, add queues/retries, stronger auth, and robust catalog/fees integrations.
