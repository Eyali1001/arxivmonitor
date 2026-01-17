# arXiv Trends Dashboard

A full-stack application to visualize arXiv publication trends by category, identifying "hot" research areas with increasing publications and declining areas.

## Features

- **Trend Visualization**: Interactive line charts showing publication counts over time
- **Category Browser**: Hierarchical dropdown with 38 arXiv subcategories across CS, Stats, Math, Physics, and more
- **Hype Indicators**: Automatically identifies trending and cooling research areas
- **Historical Data**: Tracks monthly publication counts from 2022 to present

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  FastAPI Backend│────▶│   SQLite DB     │
│  (Vite + Recharts)    │  (REST API)     │◀────│   (Metadata)    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  arXiv OAI-PMH  │
                        │  API            │
                        └─────────────────┘
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, aiosqlite
- **Frontend**: React, Vite, Recharts, Axios
- **Data Collection**: arXiv OAI-PMH protocol

## Project Structure

```
arxiv/
├── backend/
│   ├── main.py              # FastAPI app & endpoints
│   ├── database.py          # SQLite schema & category definitions
│   ├── arxiv_collector.py   # OAI-PMH data collector with retry logic
│   ├── scheduler.py         # Background task scheduler
│   ├── test_scraper.py      # Test suite for data collection
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app with styling
│   │   ├── api.js           # API client
│   │   └── components/
│   │       ├── Dashboard.jsx
│   │       ├── CategorySelector.jsx
│   │       ├── TrendChart.jsx
│   │       └── HypeIndicator.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Quick Start

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Data Collection

The app uses arXiv's OAI-PMH protocol for reliable metadata harvesting with:

- **Retry logic**: Exponential backoff (5 retries)
- **Rate limiting**: 3-second delay between requests
- **Checkpointing**: Resume interrupted syncs
- **Logging**: File-based logs for monitoring

### Initial Data Sync

Run the test suite first:
```bash
cd backend
source venv/bin/activate
python3 test_scraper.py
```

Then trigger a full sync:
```bash
curl -X POST 'http://localhost:8000/api/sync?full=true'
```

Monitor progress:
```bash
tail -f logs/sync_*.log
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | List all categories with parent grouping |
| GET | `/api/trends/{category_id}` | Monthly publication counts |
| GET | `/api/trends/{category_id}/stats` | Trend analysis with hype score |
| GET | `/api/hype` | Top trending categories |
| GET | `/api/declining` | Categories with declining publications |

## Hype Score Algorithm

The hype score compares recent 3-month average publications to the previous 3-month average:

```python
growth_rate = (recent_avg - previous_avg) / previous_avg * 100
hype_score = max(-100, min(100, growth_rate))
```

- **> 20**: Rising (hot topic)
- **5 to 20**: Growing
- **-5 to 5**: Stable
- **-20 to -5**: Cooling
- **< -20**: Declining

## Categories Tracked

**Computer Science**: AI, CL, CV, LG, NE, RO, SE, CR, DB, DC, HC, IR, PL, SY

**Statistics**: ML, TH, ME, AP

**Mathematics**: OC, PR, ST, NA

**Physics**: quant-ph, cond-mat, hep-th, gr-qc

**Electrical Engineering**: AS, IV, SP, SY

**Quantitative Biology**: BM, GN, NC, QM

**Quantitative Finance**: CP, PM, RM, ST

## License

MIT
