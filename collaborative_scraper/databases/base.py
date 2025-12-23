import sqlite3
import json
from collaborative_scraper.parse_html.base import ScrapedElement
from pathlib import Path

class ScraperDatabase:
    # These are controlled by the programmer of the extension and will be used by the user to select the path to the db
    db_key = "default_db" # -> How is the database called in the config file 
    db_name = "default.db" # Is there a case where people may want multiple db for the same scraper ?....

    def __init__(self, db_path: Path):
        self.db_path = db_path / self.db_name
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if ":" in str(self.db_path):
            print(f"ERROR: {self.db_path}")
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Create tables if they don't exist"""
        raise NotImplementedError

    # --- Database helper functions ---
    def save_element(self, element: ScrapedElement) -> None:
        raise NotImplementedError

    def update_element(self, element: ScrapedElement) -> None:
        raise NotImplementedError

    def pop_next_fetch_request(self) -> str | None:
        return None