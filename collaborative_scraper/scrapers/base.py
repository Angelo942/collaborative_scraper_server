from enum import Enum, auto
from collections.abc import Callable
from collaborative_scraper.parse_html.base import ScrapedElement
from collaborative_scraper.databases.base import ScraperDatabase
import logging

logger = logging.getLogger(__name__)

class Phase(Enum):
    """
    Progress marker for a single server-assigned fetch.

    Each scraper defines its *own* ``Phase`` enum with as many intermediate
    steps as its crawl needs (e.g. ``SEARCH_REFERENCES``, ``SEARCH_COMMENTS``,
    ...). The one fixed rule: ``DONE`` must be ``0``, the shared "request
    finished" value the server checks for.
    """
    DONE = 0
    STARTED = auto()

class RequestData:
    """
    The context the server keeps in memory related to a specific server-assigned fetch request.

    When the scraper asks for a page (see ``generate_request``), it returns a
    ``RequestData`` alongside the URL. The server stores it against the fetch
    token and hands the *same* object back to ``update`` / ``next_state`` /
    ``success`` once the client returns that page, so the scraper can tell which
    request a result belongs to and how far along it is.

    Attributes:
        requested_element: Whatever the scraper asked about (an element, an id,
            a search term - the scraper decides).
        fetch_phase: The current ``Phase`` of this request.

    Subclasses may attach their own attributes to a ``RequestData`` instance to
    carry state across the request parsing.
    """

    def __init__(self, requested_element: ScrapedElement, fetch_phase: Phase):
        self.requested_element = requested_element
        self.fetch_phase = fetch_phase

    def __repr__(self):
        return f"{self.requested_element=}, {self.fetch_phase}"

class BaseScraper:
    """
    Base class for a plugin's scraper - the object that decides what to keep and,
    in active mode, where to crawl next. Subclass it and override the hooks below.

    The server owns all crawl state (clients are stateless) and drives the scraper
    through ``POST /receive``. For each page a client posts, it calls, in order:

      * no token (the client navigated on its own)
          - ``unknown_page(elements, url)``
      * token present (a page this scraper asked for came back)
          - ``update(element, request_data)`` once per parsed element
          - ``next_state(request_data)`` -> the request's new ``Phase``
          - ``success(request_data)`` iff that phase is ``DONE``
      * then, only if the client allows redirects (active mode)
          - ``generate_request(request_data)`` -> the next page to fetch

    What to override depends on the mode you chose:

      * Passive (the client leads, the server never redirects): override only
        ``unknown_page`` - save the elements you are shown and stop.
      * Active (the server leads the crawl): override ``update``, ``next_state``,
        ``generate_request`` (and ``success`` if you need a completion hook), plus
        usually ``unknown_page`` to seed the crawl from the first page.
    """

    def __init__(self, db: ScraperDatabase, blacklist: Callable[[ScrapedElement], bool] = lambda element: False):
        """
        Args:
            db: The plugin's database instance (a ``ScraperDatabase`` subclass).
                It is the scraper's only persistence layer - call your own
                ``save_*`` / ``load_*`` helpers on it.
            blacklist: Optional predicate; return ``True`` for an element that
                should never be explored. Used by the default frontier only.
        """
        self.db = db
        self.blacklist = blacklist
        self.candidate_queue = []      # elements discovered but not yet fetched
        self.candidate_waiting = []     # elements currently being fetched
        self.special_request = False

    # We should maybe rename instead to something that says it was a page not explicitly requested
    def unknown_page(self, elements: list[ScrapedElement], url: str) -> None:
        """
        Handle a page the client navigated to on its own (no fetch token).

        The only hook a passive scraper needs: persist the elements and return.
        An active scraper may also find a uses to it.

        Args:
            elements: The parsed elements from the visited page.
        """
        pass

    def update(self, element: ScrapedElement, request_data: RequestData = None) -> None:
        """
        Integrate one element from a page this scraper asked for.

        Called once per parsed element of a server-assigned fetch, before
        ``next_state``. Required for active scrapers; unused in passive mode.

        Args:
            element: A parsed element from the returned page.
            request_data: The context of the fetch that produced it.
        """
        raise NotImplementedError

    def next_state(self, request_data: RequestData) -> Phase:
        """
        Advance a fetch after all its elements have been ``update``d, and return
        its new ``Phase`` - ``Phase.DONE`` when the fetch is complete, or an
        intermediate phase if more pages are still expected. Required for active
        scrapers.

        Args:
            request_data: The context of the fetch being advanced.

        Returns:
            The updated ``Phase`` for this request.
        """
        raise NotImplementedError

    def success(self, request_data: RequestData) -> None:
        """
        Completion hook: called once when ``next_state`` returns ``Phase.DONE``,
        i.e. every result for the fetch is in. Finalise the request here (mark it
        done, drop it from your queue, ...). Optional; default is a no-op.

        Args:
            request_data: The context of the just-completed fetch.
        """
        pass

    def generate_request(self, request_data: RequestData = None) -> tuple[str, RequestData] | tuple[None, None]:
        """
        Choose the next page for the client to fetch (active mode only).

        Called when the client allows redirects. Return ``(url, RequestData)``
        to fetch next, or ``(None, None)`` to stop the crawl. Required for
        active scrapers.

        Args:
            request_data: The fetch that just completed, or ``None`` after a
                spontaneous page.

        Returns:
            A ``(url, request_data)`` pair, or ``(None, None)`` when finished.
        """
        raise NotImplementedError