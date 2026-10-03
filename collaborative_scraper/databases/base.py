import sqlite3
import json
from collaborative_scraper.parse_html.base import ScrapedElement
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

class ScraperDatabase:
    """
    Base class for a plugin's SQLite store.

    Subclass it, create your tables in ``_init_db``, and add the persistence
    helpers your scraper calls (e.g. ``save_page`` / ``load_pending_queries``)
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._enable_wal()
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """
        Yield a connection for one unit of work, and always close it::

            with self._connect() as conn:
                conn.execute("INSERT ...", (...,))

        The block is a transaction: it commits when it exits cleanly and rolls
        back if it raises an exception. The connection is closed either way.

        One block is one connection: never open a second one inside the first,
        as the outer block holds a write lock.
        """
        conn = sqlite3.connect(self.db_path, timeout=5)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _enable_wal(self) -> None:
        """
        Put the database file in WAL mode, once, on construction.

        WAL lets readers work while a write is in flight..
        """
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")

    def _init_db(self) -> None:
        """Create the tables for the database. Called once on construction."""
        raise NotImplementedError