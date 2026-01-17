import aiosqlite
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "arxiv_trends.db"


async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize database schema."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            -- Categories table
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT,
                parent_category TEXT
            );

            -- Monthly publication counts
            CREATE TABLE IF NOT EXISTS publication_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id TEXT,
                year INTEGER,
                month INTEGER,
                count INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                UNIQUE(category_id, year, month)
            );

            -- Metadata for tracking sync state
            CREATE TABLE IF NOT EXISTS sync_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        await db.commit()


# arXiv category definitions
ARXIV_CATEGORIES = {
    "cs": {
        "name": "Computer Science",
        "subcategories": {
            "cs.AI": "Artificial Intelligence",
            "cs.CL": "Computation and Language",
            "cs.CV": "Computer Vision and Pattern Recognition",
            "cs.LG": "Machine Learning",
            "cs.NE": "Neural and Evolutionary Computing",
            "cs.RO": "Robotics",
            "cs.SE": "Software Engineering",
            "cs.CR": "Cryptography and Security",
            "cs.DB": "Databases",
            "cs.DC": "Distributed, Parallel, and Cluster Computing",
            "cs.HC": "Human-Computer Interaction",
            "cs.IR": "Information Retrieval",
            "cs.PL": "Programming Languages",
            "cs.SY": "Systems and Control",
        }
    },
    "stat": {
        "name": "Statistics",
        "subcategories": {
            "stat.ML": "Machine Learning",
            "stat.TH": "Statistics Theory",
            "stat.ME": "Methodology",
            "stat.AP": "Applications",
        }
    },
    "math": {
        "name": "Mathematics",
        "subcategories": {
            "math.OC": "Optimization and Control",
            "math.PR": "Probability",
            "math.ST": "Statistics Theory",
            "math.NA": "Numerical Analysis",
        }
    },
    "physics": {
        "name": "Physics",
        "subcategories": {
            "quant-ph": "Quantum Physics",
            "cond-mat": "Condensed Matter",
            "hep-th": "High Energy Physics - Theory",
            "gr-qc": "General Relativity and Quantum Cosmology",
        }
    },
    "eess": {
        "name": "Electrical Engineering and Systems Science",
        "subcategories": {
            "eess.AS": "Audio and Speech Processing",
            "eess.IV": "Image and Video Processing",
            "eess.SP": "Signal Processing",
            "eess.SY": "Systems and Control",
        }
    },
    "q-bio": {
        "name": "Quantitative Biology",
        "subcategories": {
            "q-bio.BM": "Biomolecules",
            "q-bio.GN": "Genomics",
            "q-bio.NC": "Neurons and Cognition",
            "q-bio.QM": "Quantitative Methods",
        }
    },
    "q-fin": {
        "name": "Quantitative Finance",
        "subcategories": {
            "q-fin.CP": "Computational Finance",
            "q-fin.PM": "Portfolio Management",
            "q-fin.RM": "Risk Management",
            "q-fin.ST": "Statistical Finance",
        }
    },
}


async def seed_categories():
    """Seed database with arXiv categories."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for parent_id, parent_data in ARXIV_CATEGORIES.items():
            # Insert parent category
            await db.execute(
                "INSERT OR IGNORE INTO categories (id, name, parent_category) VALUES (?, ?, NULL)",
                (parent_id, parent_data["name"])
            )
            # Insert subcategories
            for sub_id, sub_name in parent_data["subcategories"].items():
                await db.execute(
                    "INSERT OR IGNORE INTO categories (id, name, parent_category) VALUES (?, ?, ?)",
                    (sub_id, sub_name, parent_id)
                )
        await db.commit()
