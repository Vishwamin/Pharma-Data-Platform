import sys
from pathlib import Path
from sqlalchemy import text

# Ensure project root is in Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.database import engine
from src.logger import get_logger

logger = get_logger("SQLAnalyticsRunner")

def execute_sql_file(sql_file_path: Path):
    """Reads and executes SQL queries from a .sql file, printing results."""
    logger.info(f"--- Executing SQL Module: {sql_file_path.name} ---")
    
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split queries by semicolon to handle multiple statements safely
    queries = [q.strip() for q in sql_content.split(";") if q.strip() and not q.strip().startswith("--")]

    with engine.connect() as conn:
        for idx, query_str in enumerate(queries, 1):
            # Skip pure comments or empty lines
            clean_query = "\n".join([line for line in query_str.splitlines() if not line.strip().startswith("--")]).strip()
            if not clean_query:
                continue

            logger.info(f"Executing Query #{idx} from {sql_file_path.name}...")
            
            try:
                result = conn.execute(text(clean_query))
                if result.returns_rows:
                    rows = result.fetchmany(5)  # Fetch top 5 rows
                    cols = result.keys()
                    print(f"\n[Query #{idx} Column Headers]: {list(cols)}")
                    for row in rows:
                        print(f"  {dict(zip(cols, row))}")
                    print(f"  ... (showing top {len(rows)} sample rows)\n")
                else:
                    conn.commit()
                    print(f"  [Command Executed Successfully]\n")
            except Exception as e:
                logger.error(f"Error executing Query #{idx}: {str(e)}")

def run_all_sql_modules():
    sql_dir = Path(__file__).resolve().parent.parent / "sql"
    sql_files = sorted(sql_dir.glob("*.sql"))
    
    if not sql_files:
        logger.error(f"No SQL files found in directory: {sql_dir}")
        return

    logger.info(f"Found {len(sql_files)} SQL analytical modules to execute.")
    for sql_file in sql_files:
        execute_sql_file(sql_file)

if __name__ == "__main__":
    run_all_sql_modules()
