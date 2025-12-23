import sqlite3
import json
from collaborative_scraper.databases.base import ScraperDatabase
from collaborative_scraper.parse_html.extra.science_article import Article
from collections import Counter

class ArticleDatabase(ScraperDatabase):
    db_name = "debug.db"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def _init_db(self) -> None:
        """Create tables if they don't exist"""
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY,
                title TEXT,
                year INTEGER,
                pdf TEXT,
                num_citing INTEGER,
                num_cited INTEGER,
                citing TEXT,
                cited TEXT,
                explored INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                query TEXT NOT NULL,
                response TEXT,
                site TEXT NOT NULL,
                PRIMARY KEY (query, site)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fetch_requests (
                paper_id INTEGER PRIMARY KEY
            )
        """)
        conn.commit()
        conn.close()

    # --- Database helper functions ---
    def save_element(self, article: Article) -> None:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO pages (id, title, year, pdf, num_citing, num_cited, citing, cited, explored)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.id,
                article.title,
                article.year,
                article.pdf,
                article.num_citing,
                article.num_cited,
                json.dumps(article.citing),
                json.dumps(article.cited),
                int(article.explored)
            ))
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise RuntimeError(f"[DB] Page with id={article.id!r} already exists") from e
        finally:
            conn.close()

    def update_element(self, article: Article) -> None:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE pages
                SET title=?, year=?, pdf=?, num_citing=?, num_cited=?, citing=?, cited=?, explored=?
                WHERE id=?
            """, (
                article.title,
                article.year,
                article.pdf,
                article.num_citing,
                article.num_cited,
                json.dumps(article.citing),
                json.dumps(article.cited),
                int(article.explored),
                article.id
            ))
            if cur.rowcount == 0:
                raise RuntimeError(f"[DB] Page with id={article.id!r} not found for update")
            conn.commit()
        finally:
            conn.close()

    def get_articles(self) -> list[Article]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, title, year, pdf, num_citing, num_cited, citing, cited, explored FROM pages")
        rows = cur.fetchall()
        conn.close()
        return [Article(*r) for r in rows]

    def save_query(self, query: str, response: list[int], site: str) -> None:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO queries (query, response, site)
                VALUES (?, ?, ?)
            """, (
                query,
                json.dumps(response),
                site
            ))
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise RuntimeError(f"[DB] Query {query} already exists") from e
        finally:
            conn.close()

    def get_queries(self) -> list[str]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT query FROM queries")
        rows = cur.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_query_results(self, query: str) -> list[int]:
        conn = self._connect()
        cur = conn.cursor()
        row = cur.execute("SELECT response FROM queries WHERE query = ?", (query,)).fetchone()
        conn.close()
        if not row:
            return []
        ids = json.loads(row[0])
        return ids if ids else []

    def get_unexplored(self) -> list[int]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pages WHERE explored = 0")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def get_popular_words(self) -> dict[str, int]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT title FROM pages")
        rows = cur.fetchall()
        conn.close()
        counter = Counter()
        for r in rows:
            for word in r[0].lower().split():
                counter[word] += 1
        return counter

    def pop_next_fetch_request(self) -> int:
        conn = self._connect()
        cur = conn.cursor()
        row = cur.execute("SELECT paper_id FROM fetch_requests ORDER BY rowid ASC LIMIT 1").fetchone()
        if not row:
            conn.close()
            return None
        paper_id = int(row[0])
        cur.execute("DELETE FROM fetch_requests WHERE paper_id = ?", (paper_id,))
        conn.commit()
        conn.close()
        return paper_id