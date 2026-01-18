from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import aiosqlite
from database import DATABASE_PATH, init_db, seed_categories, ARXIV_CATEGORIES
from arxiv_collector import collector
from scheduler import start_scheduler, stop_scheduler
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await seed_categories()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    await collector.close()


app = FastAPI(title="arXiv Trends Dashboard API", lifespan=lifespan)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class Category(BaseModel):
    id: str
    name: str
    parent_category: Optional[str] = None


class CategoryGroup(BaseModel):
    id: str
    name: str
    subcategories: list[Category]


class MonthlyCount(BaseModel):
    year: int
    month: int
    count: int


class TrendStats(BaseModel):
    category_id: str
    category_name: str
    total_papers: int
    average_monthly: float
    hype_score: float
    trend_direction: str
    recent_growth_percent: float


class SyncStatus(BaseModel):
    is_syncing: bool
    progress: str
    current: int = 0
    total: int = 0
    last_sync: Optional[str] = None


def filter_valid_counts(counts: list[int]) -> list[int]:
    """
    Filter out invalid data points:
    - Zero counts (incomplete months)
    - Suspiciously low counts (data collection errors)
    """
    if not counts:
        return []

    # Calculate median to detect outliers
    sorted_counts = sorted([c for c in counts if c > 0])
    if not sorted_counts:
        return []

    median = sorted_counts[len(sorted_counts) // 2]

    # Filter out zeros and values that are less than 5% of median (likely errors)
    threshold = max(5, median * 0.05)
    return [c for c in counts if c >= threshold]


def calculate_hype_score(monthly_counts: list[int]) -> float:
    """
    Calculate hype score based on recent growth trends.
    Higher weight for more recent months.
    Returns score from -100 (declining) to +100 (hyped)
    """
    # Filter out invalid data points
    valid_counts = filter_valid_counts(monthly_counts)

    if len(valid_counts) < 6:
        return 0.0

    recent_3m = valid_counts[-3:]
    previous_3m = valid_counts[-6:-3]

    recent_avg = sum(recent_3m) / len(recent_3m)
    previous_avg = sum(previous_3m) / len(previous_3m)

    if previous_avg == 0:
        return 0.0

    growth_rate = (recent_avg - previous_avg) / previous_avg * 100
    return max(-100.0, min(100.0, growth_rate))


def get_trend_direction(hype_score: float) -> str:
    """Get trend direction label based on hype score."""
    if hype_score > 20:
        return "rising"
    elif hype_score > 5:
        return "growing"
    elif hype_score < -20:
        return "declining"
    elif hype_score < -5:
        return "cooling"
    else:
        return "stable"


@app.get("/api/categories", response_model=list[CategoryGroup])
async def get_categories():
    """List all categories grouped by parent."""
    result = []
    for parent_id, parent_data in ARXIV_CATEGORIES.items():
        subcategories = [
            Category(id=sub_id, name=sub_name, parent_category=parent_id)
            for sub_id, sub_name in parent_data["subcategories"].items()
        ]
        result.append(CategoryGroup(
            id=parent_id,
            name=parent_data["name"],
            subcategories=subcategories
        ))
    return result


@app.get("/api/trends/{category_id}", response_model=list[MonthlyCount])
async def get_trends(category_id: str):
    """Get monthly publication counts for a category."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT year, month, count
            FROM publication_counts
            WHERE category_id = ?
            ORDER BY year, month
            """,
            (category_id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        return []

    # Filter out months with zero or very low counts (incomplete data)
    results = []
    counts = [row["count"] for row in rows]
    sorted_nonzero = sorted([c for c in counts if c > 0])
    median = sorted_nonzero[len(sorted_nonzero) // 2] if sorted_nonzero else 0
    threshold = max(5, median * 0.05) if median > 0 else 5

    for row in rows:
        if row["count"] >= threshold:
            results.append(MonthlyCount(year=row["year"], month=row["month"], count=row["count"]))

    return results


@app.get("/api/trends/{category_id}/stats", response_model=TrendStats)
async def get_trend_stats(category_id: str):
    """Get trend analysis statistics for a category."""
    # Get category name
    category_name = category_id
    for parent_data in ARXIV_CATEGORIES.values():
        if category_id in parent_data["subcategories"]:
            category_name = parent_data["subcategories"][category_id]
            break

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT year, month, count
            FROM publication_counts
            WHERE category_id = ?
            ORDER BY year, month
            """,
            (category_id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        return TrendStats(
            category_id=category_id,
            category_name=category_name,
            total_papers=0,
            average_monthly=0.0,
            hype_score=0.0,
            trend_direction="unknown",
            recent_growth_percent=0.0
        )

    counts = [row["count"] for row in rows]

    # Filter out invalid counts for calculations
    valid_counts = filter_valid_counts(counts)

    total = sum(valid_counts)
    avg = total / len(valid_counts) if valid_counts else 0

    hype_score = calculate_hype_score(counts)
    trend_direction = get_trend_direction(hype_score)

    # Calculate recent growth (last 3 months vs previous 3) using valid data
    if len(valid_counts) >= 6:
        recent = sum(valid_counts[-3:])
        previous = sum(valid_counts[-6:-3])
        recent_growth = ((recent - previous) / previous * 100) if previous > 0 else 0
    else:
        recent_growth = 0

    return TrendStats(
        category_id=category_id,
        category_name=category_name,
        total_papers=total,
        average_monthly=round(avg, 1),
        hype_score=round(hype_score, 1),
        trend_direction=trend_direction,
        recent_growth_percent=round(recent_growth, 1)
    )


@app.get("/api/hype", response_model=list[TrendStats])
async def get_hype_categories(limit: int = 10):
    """Get top trending categories (increasing publications)."""
    all_stats = []

    for parent_data in ARXIV_CATEGORIES.values():
        for sub_id in parent_data["subcategories"].keys():
            stats = await get_trend_stats(sub_id)
            if stats.total_papers > 0:  # Only include categories with data
                all_stats.append(stats)

    # Sort by hype score descending
    all_stats.sort(key=lambda x: x.hype_score, reverse=True)
    return all_stats[:limit]


@app.get("/api/declining", response_model=list[TrendStats])
async def get_declining_categories(limit: int = 10):
    """Get categories with declining publications."""
    all_stats = []

    for parent_data in ARXIV_CATEGORIES.values():
        for sub_id in parent_data["subcategories"].keys():
            stats = await get_trend_stats(sub_id)
            if stats.total_papers > 0:
                all_stats.append(stats)

    # Sort by hype score ascending (most declining first)
    all_stats.sort(key=lambda x: x.hype_score)
    return all_stats[:limit]


@app.post("/api/sync")
async def trigger_sync(background_tasks: BackgroundTasks, full: bool = False):
    """Trigger manual data sync."""
    if collector.is_syncing:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    if full:
        background_tasks.add_task(collector.sync_all_categories, 2022)
    else:
        background_tasks.add_task(collector.quick_sync)

    return {"message": "Sync started", "type": "full" if full else "quick"}


@app.get("/api/sync/status", response_model=SyncStatus)
async def get_sync_status():
    """Check sync status."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT value FROM sync_metadata WHERE key = 'last_sync'"
        )
        row = await cursor.fetchone()
        last_sync = row["value"] if row else None

    return SyncStatus(
        is_syncing=collector.is_syncing,
        progress=collector.sync_progress,
        current=collector.current,
        total=collector.total,
        last_sync=last_sync
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
