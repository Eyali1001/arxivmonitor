import httpx
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite
from database import DATABASE_PATH, ARXIV_CATEGORIES
import logging
import json
import re
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

# OAI-PMH base URL (use the new endpoint directly to avoid redirect overhead)
OAI_BASE_URL = "https://oaipmh.arxiv.org/oai"

# OAI-PMH namespaces
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
}

# Configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 5  # seconds
REQUEST_TIMEOUT = 120  # seconds (OAI-PMH can be slow)
RATE_LIMIT_DELAY = 3  # seconds between requests

# Map category IDs to OAI-PMH set specs - ALL categories
CATEGORY_TO_SETSPEC = {
    # CS - Computer Science
    "cs.AI": "cs:cs:AI",
    "cs.AR": "cs:cs:AR",
    "cs.CC": "cs:cs:CC",
    "cs.CE": "cs:cs:CE",
    "cs.CG": "cs:cs:CG",
    "cs.CL": "cs:cs:CL",
    "cs.CR": "cs:cs:CR",
    "cs.CV": "cs:cs:CV",
    "cs.CY": "cs:cs:CY",
    "cs.DB": "cs:cs:DB",
    "cs.DC": "cs:cs:DC",
    "cs.DL": "cs:cs:DL",
    "cs.DM": "cs:cs:DM",
    "cs.DS": "cs:cs:DS",
    "cs.ET": "cs:cs:ET",
    "cs.FL": "cs:cs:FL",
    "cs.GL": "cs:cs:GL",
    "cs.GR": "cs:cs:GR",
    "cs.GT": "cs:cs:GT",
    "cs.HC": "cs:cs:HC",
    "cs.IR": "cs:cs:IR",
    "cs.IT": "cs:cs:IT",
    "cs.LG": "cs:cs:LG",
    "cs.LO": "cs:cs:LO",
    "cs.MA": "cs:cs:MA",
    "cs.MM": "cs:cs:MM",
    "cs.MS": "cs:cs:MS",
    "cs.NA": "cs:cs:NA",
    "cs.NE": "cs:cs:NE",
    "cs.NI": "cs:cs:NI",
    "cs.OH": "cs:cs:OH",
    "cs.OS": "cs:cs:OS",
    "cs.PF": "cs:cs:PF",
    "cs.PL": "cs:cs:PL",
    "cs.RO": "cs:cs:RO",
    "cs.SC": "cs:cs:SC",
    "cs.SD": "cs:cs:SD",
    "cs.SE": "cs:cs:SE",
    "cs.SI": "cs:cs:SI",
    "cs.SY": "cs:cs:SY",
    # ECON - Economics
    "econ.EM": "econ:econ:EM",
    "econ.GN": "econ:econ:GN",
    "econ.TH": "econ:econ:TH",
    # EESS - Electrical Engineering and Systems Science
    "eess.AS": "eess:eess:AS",
    "eess.IV": "eess:eess:IV",
    "eess.SP": "eess:eess:SP",
    "eess.SY": "eess:eess:SY",
    # MATH - Mathematics
    "math.AC": "math:math:AC",
    "math.AG": "math:math:AG",
    "math.AP": "math:math:AP",
    "math.AT": "math:math:AT",
    "math.CA": "math:math:CA",
    "math.CO": "math:math:CO",
    "math.CT": "math:math:CT",
    "math.CV": "math:math:CV",
    "math.DG": "math:math:DG",
    "math.DS": "math:math:DS",
    "math.FA": "math:math:FA",
    "math.GM": "math:math:GM",
    "math.GN": "math:math:GN",
    "math.GR": "math:math:GR",
    "math.GT": "math:math:GT",
    "math.HO": "math:math:HO",
    "math.IT": "math:math:IT",
    "math.KT": "math:math:KT",
    "math.LO": "math:math:LO",
    "math.MG": "math:math:MG",
    "math.MP": "math:math:MP",
    "math.NA": "math:math:NA",
    "math.NT": "math:math:NT",
    "math.OA": "math:math:OA",
    "math.OC": "math:math:OC",
    "math.PR": "math:math:PR",
    "math.QA": "math:math:QA",
    "math.RA": "math:math:RA",
    "math.RT": "math:math:RT",
    "math.SG": "math:math:SG",
    "math.SP": "math:math:SP",
    "math.ST": "math:math:ST",
    # PHYSICS
    "astro-ph.CO": "physics:astro-ph:CO",
    "astro-ph.EP": "physics:astro-ph:EP",
    "astro-ph.GA": "physics:astro-ph:GA",
    "astro-ph.HE": "physics:astro-ph:HE",
    "astro-ph.IM": "physics:astro-ph:IM",
    "astro-ph.SR": "physics:astro-ph:SR",
    "cond-mat.dis-nn": "physics:cond-mat:dis-nn",
    "cond-mat.mes-hall": "physics:cond-mat:mes-hall",
    "cond-mat.mtrl-sci": "physics:cond-mat:mtrl-sci",
    "cond-mat.other": "physics:cond-mat:other",
    "cond-mat.quant-gas": "physics:cond-mat:quant-gas",
    "cond-mat.soft": "physics:cond-mat:soft",
    "cond-mat.stat-mech": "physics:cond-mat:stat-mech",
    "cond-mat.str-el": "physics:cond-mat:str-el",
    "cond-mat.supr-con": "physics:cond-mat:supr-con",
    "gr-qc": "physics:gr-qc",
    "hep-ex": "physics:hep-ex",
    "hep-lat": "physics:hep-lat",
    "hep-ph": "physics:hep-ph",
    "hep-th": "physics:hep-th",
    "math-ph": "physics:math-ph",
    "nlin.AO": "physics:nlin:AO",
    "nlin.CD": "physics:nlin:CD",
    "nlin.CG": "physics:nlin:CG",
    "nlin.PS": "physics:nlin:PS",
    "nlin.SI": "physics:nlin:SI",
    "nucl-ex": "physics:nucl-ex",
    "nucl-th": "physics:nucl-th",
    "physics.acc-ph": "physics:physics:acc-ph",
    "physics.ao-ph": "physics:physics:ao-ph",
    "physics.app-ph": "physics:physics:app-ph",
    "physics.atm-clus": "physics:physics:atm-clus",
    "physics.atom-ph": "physics:physics:atom-ph",
    "physics.bio-ph": "physics:physics:bio-ph",
    "physics.chem-ph": "physics:physics:chem-ph",
    "physics.class-ph": "physics:physics:class-ph",
    "physics.comp-ph": "physics:physics:comp-ph",
    "physics.data-an": "physics:physics:data-an",
    "physics.ed-ph": "physics:physics:ed-ph",
    "physics.flu-dyn": "physics:physics:flu-dyn",
    "physics.gen-ph": "physics:physics:gen-ph",
    "physics.geo-ph": "physics:physics:geo-ph",
    "physics.hist-ph": "physics:physics:hist-ph",
    "physics.ins-det": "physics:physics:ins-det",
    "physics.med-ph": "physics:physics:med-ph",
    "physics.optics": "physics:physics:optics",
    "physics.plasm-ph": "physics:physics:plasm-ph",
    "physics.pop-ph": "physics:physics:pop-ph",
    "physics.soc-ph": "physics:physics:soc-ph",
    "physics.space-ph": "physics:physics:space-ph",
    "quant-ph": "physics:quant-ph",
    # Q-BIO - Quantitative Biology
    "q-bio.BM": "q-bio:q-bio:BM",
    "q-bio.CB": "q-bio:q-bio:CB",
    "q-bio.GN": "q-bio:q-bio:GN",
    "q-bio.MN": "q-bio:q-bio:MN",
    "q-bio.NC": "q-bio:q-bio:NC",
    "q-bio.OT": "q-bio:q-bio:OT",
    "q-bio.PE": "q-bio:q-bio:PE",
    "q-bio.QM": "q-bio:q-bio:QM",
    "q-bio.SC": "q-bio:q-bio:SC",
    "q-bio.TO": "q-bio:q-bio:TO",
    # Q-FIN - Quantitative Finance
    "q-fin.CP": "q-fin:q-fin:CP",
    "q-fin.EC": "q-fin:q-fin:EC",
    "q-fin.GN": "q-fin:q-fin:GN",
    "q-fin.MF": "q-fin:q-fin:MF",
    "q-fin.PM": "q-fin:q-fin:PM",
    "q-fin.PR": "q-fin:q-fin:PR",
    "q-fin.RM": "q-fin:q-fin:RM",
    "q-fin.ST": "q-fin:q-fin:ST",
    "q-fin.TR": "q-fin:q-fin:TR",
    # STAT - Statistics
    "stat.AP": "stat:stat:AP",
    "stat.CO": "stat:stat:CO",
    "stat.ME": "stat:stat:ME",
    "stat.ML": "stat:stat:ML",
    "stat.OT": "stat:stat:OT",
    "stat.TH": "stat:stat:TH",
}


def parse_arxiv_id_date(identifier: str) -> tuple[int, int] | None:
    """Extract submission year/month from arXiv identifier.

    ArXiv IDs follow the format YYMM.xxxxx (since April 2007).
    For example: oai:arXiv.org:2401.12345 -> (2024, 1) for January 2024

    Returns (year, month) or None if can't parse.
    """
    match = re.search(r'(\d{4})\.\d+', identifier)
    if match:
        yymm = match.group(1)
        yy = int(yymm[:2])
        mm = int(yymm[2:])
        # 2-digit year: 07+ maps to 2007+
        year = 2000 + yy
        if 1 <= mm <= 12:
            return (year, mm)
    return None


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

    async def count_papers_by_submission_date(
        self,
        parent_set: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int
    ) -> dict[tuple[int, int], dict[str, int]]:
        """
        Count papers by their actual submission date (from arXiv ID).

        Unlike OAI-PMH date filters (which use modification date), this method
        extracts the submission year/month from the arXiv identifier (YYMM.xxxxx).

        Returns dict mapping (year, month) -> {category_id: count}
        """
        # Build mapping from setSpec to category_id for this parent
        setspec_to_category = {}
        for cat_id, setspec in CATEGORY_TO_SETSPEC.items():
            if setspec.startswith(f"{parent_set}:"):
                setspec_to_category[setspec] = cat_id

        # Counts: (year, month) -> category_id -> count
        counts = defaultdict(lambda: defaultdict(int))
        total_records = 0
        pages = 0

        # Query all records for this parent set
        # We use a date filter to avoid fetching very old records, but we'll
        # verify submission date from the arXiv ID
        params = {
            "verb": "ListIdentifiers",
            "metadataPrefix": "oai_dc",
            "set": parent_set,
            "from": f"{start_year}-{start_month:02d}-01",
        }

        while True:
            pages += 1
            root, token = await self.fetch_oai_page(params)

            if root is None:
                break

            # Process each record
            for header in root.findall(".//oai:header", OAI_NS):
                if header.get("status") == "deleted":
                    continue

                # Get the arXiv identifier
                identifier = header.find("oai:identifier", OAI_NS)
                if identifier is None or not identifier.text:
                    continue

                # Parse submission date from arXiv ID
                submission_date = parse_arxiv_id_date(identifier.text)
                if submission_date is None:
                    continue

                sub_year, sub_month = submission_date

                # Check if submission is within our target range
                if sub_year < start_year or (sub_year == start_year and sub_month < start_month):
                    continue
                if sub_year > end_year or (sub_year == end_year and sub_month > end_month):
                    continue

                total_records += 1
                key = (sub_year, sub_month)

                # Count for each category the paper belongs to
                for setspec_elem in header.findall("oai:setSpec", OAI_NS):
                    setspec = setspec_elem.text
                    if setspec and setspec in setspec_to_category:
                        cat_id = setspec_to_category[setspec]
                        counts[key][cat_id] += 1

            if not token:
                break

            # Continue with resumption token
            params = {"verb": "ListIdentifiers", "resumptionToken": token}

            if pages % 10 == 0:
                logger.info(f"    {parent_set}: processed {pages} pages, {total_records} records so far")

            await asyncio.sleep(RATE_LIMIT_DELAY)

        logger.info(f"  {parent_set}: {total_records} papers in {pages} pages")
        return dict(counts)

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

    async def sync_all_papers_by_parent(
        self,
        parent_set: str,
        start_year: int,
        end_year: int,
        end_month: int
    ) -> dict[tuple[int, int], dict[str, int]]:
        """
        Fetch all papers for a parent set and count by actual submission date.
        Returns dict mapping (year, month) -> {category_id: count}
        """
        self._sync_progress = f"Fetching {parent_set} papers..."
        logger.info(f"Fetching {parent_set} papers...")

        counts = await self.count_papers_by_submission_date(
            parent_set, start_year, 1, end_year, end_month
        )

        return counts

    async def sync_all_categories(self, start_year: int = 2022, resume: bool = True):
        """
        Sync all categories with checkpoint/resume support.

        NEW APPROACH: Fetches all papers per parent set, then extracts the
        actual submission date from the arXiv ID (YYMM.xxxxx format).
        This fixes the issue where OAI-PMH date filters use modification date.
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
            now = datetime.now()
            end_year = now.year
            end_month = now.month - 1  # Exclude current incomplete month
            if end_month == 0:
                end_month = 12
                end_year -= 1

            parent_sets = ["cs", "econ", "eess", "math", "physics", "q-bio", "q-fin", "stat"]
            self._total = len(parent_sets)

            # Check for checkpoint to resume
            checkpoint = self.load_checkpoint() if resume else None
            start_index = 0
            existing_counts = {}

            if checkpoint and checkpoint.get("type") == "full_sync_v2":
                start_index = checkpoint.get("parent_index", 0)
                existing_counts = checkpoint.get("counts", {})
                # Convert string keys back to tuples
                existing_counts = {
                    eval(k): v for k, v in existing_counts.items()
                }
                logger.info(f"Resuming from checkpoint: parent index {start_index}")

            # Aggregate all counts: (year, month) -> category_id -> count
            all_counts = defaultdict(lambda: defaultdict(int))
            for key, cats in existing_counts.items():
                for cat_id, count in cats.items():
                    all_counts[key][cat_id] = count

            for i, parent_set in enumerate(parent_sets):
                if i < start_index:
                    self._current = i + 1
                    continue

                self._current = i + 1
                self._sync_progress = f"Processing {parent_set} ({i+1}/{len(parent_sets)})"
                logger.info(f"\n[{i+1}/{len(parent_sets)}] Processing {parent_set}...")

                # Save checkpoint before starting
                self.save_checkpoint({
                    "type": "full_sync_v2",
                    "parent_index": i,
                    "counts": {str(k): dict(v) for k, v in all_counts.items()},
                    "timestamp": datetime.now().isoformat()
                })

                # Fetch all papers for this parent set
                counts = await self.sync_all_papers_by_parent(
                    parent_set, start_year, end_year, end_month
                )

                # Merge counts
                for key, cat_counts in counts.items():
                    for cat_id, count in cat_counts.items():
                        all_counts[key][cat_id] += count

                await asyncio.sleep(RATE_LIMIT_DELAY)

            # Save all counts to database
            logger.info(f"\nSaving counts to database...")
            self._sync_progress = "Saving to database..."

            async with aiosqlite.connect(DATABASE_PATH) as db:
                for (year, month), cat_counts in sorted(all_counts.items()):
                    for cat_id, count in cat_counts.items():
                        await db.execute("""
                            INSERT OR REPLACE INTO publication_counts
                            (category_id, year, month, count)
                            VALUES (?, ?, ?, ?)
                        """, (cat_id, year, month, count))
                        self._successful += 1

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
            logger.info(f"Total months with data: {len(all_counts)}")
            logger.info(f"Total category-month records: {self._successful}")
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
        Quick sync - sync recent months for all categories.
        Uses the corrected approach of extracting submission dates from arXiv IDs.
        """
        self._is_syncing = True
        self._sync_progress = "Quick sync in progress..."
        self._current = 0
        self._errors = 0
        self._successful = 0

        logger.info("Starting quick sync...")

        try:
            now = datetime.now()
            # Sync last 3 months (excluding current incomplete month)
            end_year = now.year
            end_month = now.month - 1
            if end_month == 0:
                end_month = 12
                end_year -= 1

            start_year = end_year
            start_month = end_month - 2
            if start_month <= 0:
                start_month += 12
                start_year -= 1

            parent_sets = ["cs", "econ", "eess", "math", "physics", "q-bio", "q-fin", "stat"]
            self._total = len(parent_sets)

            all_counts = defaultdict(lambda: defaultdict(int))

            for i, parent_set in enumerate(parent_sets):
                self._current = i + 1
                self._sync_progress = f"Fetching {parent_set}..."
                logger.info(f"  Fetching {parent_set}...")

                counts = await self.count_papers_by_submission_date(
                    parent_set, start_year, start_month, end_year, end_month
                )

                for key, cat_counts in counts.items():
                    for cat_id, count in cat_counts.items():
                        all_counts[key][cat_id] += count

                await asyncio.sleep(RATE_LIMIT_DELAY)

            # Save to database
            async with aiosqlite.connect(DATABASE_PATH) as db:
                for (year, month), cat_counts in sorted(all_counts.items()):
                    for cat_id, count in cat_counts.items():
                        await db.execute("""
                            INSERT OR REPLACE INTO publication_counts
                            (category_id, year, month, count)
                            VALUES (?, ?, ?, ?)
                        """, (cat_id, year, month, count))
                        self._successful += 1
                        logger.info(f"  {year}-{month:02d} {cat_id}: {count} papers")

                await db.execute(
                    "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)",
                    ("last_sync", datetime.now().isoformat())
                )
                await db.commit()

            self._sync_progress = "Quick sync completed"
            logger.info(f"Quick sync completed: {self._successful} category-months saved")

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
