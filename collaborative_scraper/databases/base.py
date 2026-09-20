import sqlite3
import json
from collaborative_scraper.parse_html.base import ScrapedElement
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

class ScraperDatabase:
    """
    Base class for a plugin's SQLite store - the scraper's only persistence layer.

    Subclass it, set ``db_name``, create your tables in ``_init_db``, and add the
    persistence helpers your scraper calls (name them for the task, e.g.
    ``save_page`` / ``load_pending_queries`` - the methods below are just a
    common starting shape). Register the subclass per project in ``db.py``; the
    server builds it with the per-project data directory.
    """

    # File name of this project's database, under the per-project data dir.
    db_name = "default.db"

    def __init__(self, db_path: Path):
        self.db_path = db_path / self.db_name
        self._enable_wal()
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """
        Yield a connection for one unit of work, and always close it::

            with self._connect() as conn:
                conn.execute("INSERT ...", (...,))

        The block is a transaction: it commits when it exits cleanly and rolls
        back if it raises. The connection is closed either way - note that
        sqlite3's own ``with conn:`` only ends the transaction, so closing has
        to be done here.

        One block is one connection: never open a second one inside the first,
        as the outer block holds a write lock the inner one would only wait on
        until it times out. So a method that opens a block calls only methods
        that open none - a helper meant to run inside someone else's block takes
        that ``conn`` as an argument instead and opens nothing itself (see
        ``_load_person_shallow`` in the IMDb demo).
        """
        conn = sqlite3.connect(self.db_path, timeout=30)  # before yield = __enter__
        try:
            with conn:                           # sqlite3's own CM: commit / rollback
                yield conn                       # the value handed to `as conn`
        finally:
            conn.close()                         # ours: always close

    def _enable_wal(self) -> None:
        """
        Put the database file in WAL mode, once, on construction.

        WAL lets readers work while a write is in flight, which matters because
        several clients POST to ``/receive`` concurrently. The mode is stored in
        the database file itself, so it applies to every later connection and
        only needs setting when the store is opened.
        """
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")

    def _init_db(self) -> None:
        """Create the tables if they don't exist. Called once on construction."""
        raise NotImplementedError