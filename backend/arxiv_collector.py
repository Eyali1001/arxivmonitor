import httpx
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite
from database import DATABASE_PATH, ARXIV_CATEGORIES
import logging
import json
from pathlib import Path
from collections import defaultdict

# Configure file-based logging for overnight runs
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up both console and file logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Checkpoint file for resume capability
CHECKPOINT_FILE = Path(__file__).parent / "sync_checkpoint.json"

# OAI-PMH base URL
OAI_BASE_URL = "https://export.arxiv.org/oai2"

# OAI-PMH namespaces
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
}

# Configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 5  # seconds
REQUEST_TIMEOUT = 120  # seconds (OAI-PMH can be slow)
RATE_LIMIT_DELAY = 3  # seconds between requests

# Map category IDs to OAI-PMH set specs
# OAI-PMH uses format like "cs" for parent, and records have setSpec like "cs:cs:AI"
CATEGORY_TO_SETSPEC = {
    # Computer Science
    "cs.AI": "cs:cs:AI",
    "cs.CL": "cs:cs:CL",
    "cs.CV": "cs:cs:CV",
    "cs.LG": "cs:cs:LG",
    "cs.NE": "cs:cs:NE",
    "cs.RO": "cs:cs:RO",
    "cs.SE": "cs:cs:SE",
    "cs.CR": "cs:cs:CR",
    "cs.DB": "cs:cs:DB",
    "cs.DC": "cs:cs:DC",
    "cs.HC": "cs:cs:HC",
    "cs.IR": "cs:cs:IR",
    "cs.PL": "cs:cs:PL",
    "cs.SY": "cs:cs:SY",
    # Statistics
    "stat.ML": "stat:stat:ML",
    "stat.TH": "stat:stat:TH",
    "stat.ME": "stat:stat:ME",
    "stat.AP": "stat:stat:AP",
    # Mathematics
    "math.OC": "math:math:OC",
    "math.PR": "math:math:PR",
    "math.ST": "math:math:ST",
    "math.NA": "math:math:NA",
    # Physics
    "quant-ph": "physics:quant-ph",
    "cond-mat": "physics:cond-mat",
    "hep-th": "physics:hep-th",
    "gr-qc": "physics:gr-qc",
    # EESS
    "eess.AS": "eess:eess:AS",
    "eess.IV": "eess:eess:IV",
    "eess.SP": "eess:eess:SP",
    "eess.SY": "eess:eess:SY",
    # Q-bio
    "q-bio.BM": "q-bio:q-bio:BM",
    "q-bio.GN": "q-bio:q-bio:GN",
    "q-bio.NC": "q-bio:q-bio:NC",
    "q-bio.QM": "q-bio:q-bio:QM",
    # Q-fin
    "q-fin.CP": "q-fin:q-fin:CP",
    "q-fin.PM": "q-fin:q-fin:PM",
    "q-fin.RM": "q-fin:q-fin:RM",
    "q-fin.ST": "q-fin:q-fin:ST",
}


class ArxivCollector:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=30.0),
            follow_redirects=True
        )
        self._is_syncing = False
        self._sync_progress = ""
        self._current = 0
        self._total = 0
        self._errors = 0
        self._successful = 0

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    @property
    def sync_progress(self) -> str:
        return self._sync_progress

    @property
    def current(self) -> int:
        return self._current

    @property
    def total(self) -> int:
        return self._total

    async def close(self):
        await self.client.aclose()

    async def fetch_oai_page(
        self,
        params: dict,
        retry_count: int = 0
    ) -> tuple[ET.Element | None, str | None]:
        """
        Fetch a single OAI-PMH page with retry logic.
        Returns (xml_root, resumption_token) tuple.
        """
        try:
            response = await self.client.get(OAI_BASE_URL, params=params)
            response.raise_for_status()

            root = ET.fromstring(response.text)

            # Check for OAI-PMH errors
            error = root.find(".//oai:error", OAI_NS)
            if error is not None:
                error_code = error.get("code", "unknown")
                if error_code == "noRecordsMatch":
                    # No records for this query - not an error
                    return root, None
                logger.error(f"OAI-PMH error: {error_code} - {error.text}")
                return None, None

            # Get resumption token if present
            token_elem = root.find(".//oai:resumptionToken", OAI_NS)
            token = token_elem.text if token_elem is not None and token_elem.text else None

            return root, token

        except httpx.TimeoutException as e:
            if retry_count < MAX_RETRIES:
                delay = INITIAL_RETRY_DELAY * (2 ** retry_count)
                logger.warning(f"Timeout, retrying in {delay}s... (attempt {retry_count + 1})")
                await asyncio.sleep(delay)
                return await self.fetch_oai_page(params, retry_count + 1)
            logger.error(f"All retries failed due to timeout")
            return None, None

        except Exception as e:
            if retry_count < MAX_RETRIES:
                delay = INITIAL_RETRY_DELAY * (2 ** retry_count)
                logger.warning(f"Error: {e}, retrying in {delay}s... (attempt {retry_count + 1})")
                await asyncio.sleep(delay)
                return await self.fetch_oai_page(params, retry_count + 1)
            logger.error(f"All retries failed: {e}")
            return None, None

    async def count_papers_by_category_for_month(
        self,
        year: int,
        month: int,
        parent_set: str
    ) -> dict[str, int]:
        """
        Count papers for all subcategories within a parent set for a given month.
        Uses OAI-PMH ListIdentifiers to get headers with setSpec info.
        Returns dict mapping category_id to count.
        """
        # Calculate date range for the month
        from_date = f"{year}-{month:02d}-01"
        if month == 12:
            until_date = f"{year}-12-31"
        else:
            next_month = datetime(year, month + 1, 1)
            last_day = (next_month - timedelta(days=1)).day
            until_date = f"{year}-{month:02d}-{last_day:02d}"

        counts = defaultdict(int)
        total_records = 0

        params = {
            "verb": "ListIdentifiers",
            "metadataPrefix": "oai_dc",
            "set": parent_set,
            "from": from_date,
            "until": until_date,
        }

        while True:
            root, token = await self.fetch_oai_page(params)

            if root is None:
                break

            # Count records by setSpec
            for header in root.findall(".//oai:header", OAI_NS):
                if header.get("status") == "deleted":
                    continue

                total_records += 1
                for setspec in header.findall("oai:setSpec", OAI_NS):
                    spec = setspec.text
                    if spec:
                        counts[spec] += 1

            if not token:
                break

            # Continue with resumption token
            params = {"verb": "ListIdentifiers", "resumptionToken": token}
            await asyncio.sleep(RATE_LIMIT_DELAY)

        logger.debug(f"  {parent_set} {year}-{month:02d}: {total_records} total records")
        return dict(counts)

    async def fetch_papers_count_with_retry(
        self,
        category: str,
        from_date: str,
        until_date: str
    ) -> tuple[int, bool]:
        """
        Fetch count for a single category using OAI-PMH.
        This is a simpler method for quick syncs.
        """
        setspec = CATEGORY_TO_SETSPEC.get(category)
        if not setspec:
            logger.error(f"Unknown category: {category}")
            return 0, False

        # Extract parent set from setspec (e.g., "cs:cs:AI" -> "cs")
        parent_set = setspec.split(":")[0]

        params = {
            "verb": "ListIdentifiers",
            "metadataPrefix": "oai_dc",
            "set": parent_set,
            "from": from_date,
            "until": until_date,
        }

        count = 0
        while True:
            root, token = await self.fetch_oai_page(params)

            if root is None:
                return 0, False

            # Count records matching our specific setSpec
            for header in root.findall(".//oai:header", OAI_NS):
                if header.get("status") == "deleted":
                    continue

                for spec_elem in header.findall("oai:setSpec", OAI_NS):
                    if spec_elem.text == setspec:
                        count += 1
                        break

            if not token:
                break

            params = {"verb": "ListIdentifiers", "resumptionToken": token}
            await asyncio.sleep(RATE_LIMIT_DELAY)

        return count, True

    def save_checkpoint(self, data: dict):
        """Save checkpoint to file for resume capability."""
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(data, f)
        logger.debug(f"Checkpoint saved")

    def load_checkpoint(self) -> Optional[dict]:
        """Load checkpoint from file if exists."""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return None

    def clear_checkpoint(self):
        """Clear checkpoint file after successful completion."""
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
            logger.info("Checkpoint cleared")

    async def sync_month_batch(
        self,
        year: int,
        month: int
    ) -> dict[str, int]:
        """
        Sync all categories for a single month efficiently.
        Fetches data from each parent set once and distributes counts.
        """
        all_counts = {}

        # Process each parent set
        parent_sets = ["cs", "stat", "math", "physics", "eess", "q-bio", "q-fin"]

        for parent_set in parent_sets:
            self._sync_progress = f"Fetching {parent_set} {year}-{month:02d}"
            logger.info(f"  Fetching {parent_set} for {year}-{month:02d}...")

            counts = await self.count_papers_by_category_for_month(year, month, parent_set)

            # Map OAI setSpec back to our category IDs
            for cat_id, setspec in CATEGORY_TO_SETSPEC.items():
                if setspec in counts:
                    all_counts[cat_id] = counts[setspec]

            await asyncio.sleep(RATE_LIMIT_DELAY)

        return all_counts

    async def sync_all_categories(self, start_year: int = 2022, resume: bool = True):
        """
        Sync all categories with checkpoint/resume support.
        Uses efficient batch fetching by month.
        """
        self._is_syncing = True
        self._sync_progress = "Starting sync..."
        self._current = 0
        self._errors = 0
        self._successful = 0

        logger.info("=" * 60)
        logger.info(f"Starting full sync from {start_year}")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 60)

        try:
            # Calculate total months to process
            now = datetime.now()
            end_year = now.year
            end_month = now.month

            months_to_process = []
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    if year == end_year and month > end_month:
                        break
                    months_to_process.append((year, month))

            self._total = len(months_to_process)

            # Check for checkpoint to resume
            checkpoint = self.load_checkpoint() if resume else None
            start_index = 0

            if checkpoint and checkpoint.get("type") == "full_sync":
                start_index = checkpoint.get("month_index", 0)
                logger.info(f"Resuming from checkpoint: month index {start_index}")

            for i, (year, month) in enumerate(months_to_process):
                if i < start_index:
                    continue

                self._current = i + 1
                self._sync_progress = f"Processing {year}-{month:02d}"
                logger.info(f"\n[{i+1}/{self._total}] Processing {year}-{month:02d}...")

                # Save checkpoint before starting month
                self.save_checkpoint({
                    "type": "full_sync",
                    "month_index": i,
                    "year": year,
                    "month": month,
                    "timestamp": datetime.now().isoformat()
                })

                # Fetch all counts for this month
                counts = await self.sync_month_batch(year, month)

                # Save to database
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    for cat_id, count in counts.items():
                        await db.execute("""
                            INSERT OR REPLACE INTO publication_counts
                            (category_id, year, month, count)
                            VALUES (?, ?, ?, ?)
                        """, (cat_id, year, month, count))
                        self._successful += 1

                    await db.commit()

                logger.info(f"  Saved {len(counts)} category counts for {year}-{month:02d}")

            # Update sync metadata
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)",
                    ("last_sync", datetime.now().isoformat())
                )
                await db.execute(
                    "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)",
                    ("last_full_sync", datetime.now().isoformat())
                )
                await db.commit()

            # Clear checkpoint on success
            self.clear_checkpoint()

            self._sync_progress = "Sync completed"
            logger.info("=" * 60)
            logger.info("SYNC COMPLETED")
            logger.info(f"Total successful saves: {self._successful}")
            logger.info(f"Total errors: {self._errors}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Sync failed with exception: {e}", exc_info=True)
            self._sync_progress = f"Sync failed: {e}"
            raise

        finally:
            self._is_syncing = False
            self._current = 0
            self._total = 0

    async def quick_sync(self):
        """
        Quick sync - only sync the current month for all categories.
        """
        self._is_syncing = True
        self._sync_progress = "Quick sync in progress..."
        self._current = 0
        self._errors = 0
        self._successful = 0

        logger.info("Starting quick sync...")

        try:
            now = datetime.now()
            year = now.year
            month = now.month

            self._total = 1  # Just one month

            # Fetch all counts for current month
            counts = await self.sync_month_batch(year, month)
            self._current = 1

            # Save to database
            async with aiosqlite.connect(DATABASE_PATH) as db:
                for cat_id, count in counts.items():
                    await db.execute("""
                        INSERT OR REPLACE INTO publication_counts
                        (category_id, year, month, count)
                        VALUES (?, ?, ?, ?)
                    """, (cat_id, year, month, count))
                    self._successful += 1
                    logger.info(f"  {cat_id}: {count} papers")

                await db.execute(
                    "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)",
                    ("last_sync", datetime.now().isoformat())
                )
                await db.commit()

            self._sync_progress = "Quick sync completed"
            logger.info(f"Quick sync completed: {self._successful} categories saved")

        except Exception as e:
            logger.error(f"Quick sync failed: {e}", exc_info=True)
            self._sync_progress = f"Quick sync failed: {e}"
            self._errors += 1

        finally:
            self._is_syncing = False
            self._current = 0
            self._total = 0


# Singleton instance
collector = ArxivCollector()
