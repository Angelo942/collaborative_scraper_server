from collections.abc import Callable
from enum import Enum, auto
from urllib.parse import urlencode
from collaborative_scraper.parse_html.base import ScrapedElement, Result
from collaborative_scraper.databases.base import ScraperDatabase
import logging

logger = logging.getLogger(__name__)

DONE = 0

class Phase(Enum):
    """
    Progress marker for a single server-assigned fetch.

    Each scraper defines its *own* ``Phase`` enum with as many intermediate
    steps as its crawl needs (e.g. ``SEARCH_REFERENCES``, ``SEARCH_COMMENTS``,
    ...). The one fixed rule: ``DONE`` must be ``0``, the shared "request
    finished" value the server checks for.
    """
    DONE = DONE
    STARTED = auto()

def is_done(phase: Phase) -> bool:
    return phase.value == DONE

class Request:
    """
    A page for the client to fetch, as returned by ``generate_request``.

    Use one of the subclasses; each knows the instruction that makes the
    extension fetch it. ``parameters`` is the form of a ``POSTRequest`` (what
    the parser receives as ``post_parameters`` when the page comes back), the
    JSON body of a ``FETCHRequest``, and ``None`` for a GET.
    """

    def __init__(self, url: str):
        self.url = url
        self.parameters = None

    def instruction(self) -> dict:
        raise NotImplementedError

    def __repr__(self):
        return f"{type(self).__name__}({self.url!r})"

class GETRequest(Request):
    """Navigate to ``url`` with ``parameters`` (name -> value) as its query arguments."""

    def __init__(self, url: str, parameters: dict = None):
        super().__init__(url)
        self.parameters = parameters or {}

    def link(self) -> str:
        """``url`` with ``parameters`` url-encoded into its query string."""
        if not self.parameters:
            return self.url
        separator = "&" if "?" in self.url else "?"
        return f"{self.url}{separator}{urlencode(self.parameters)}"

    def instruction(self) -> dict:
        return {"type": "GET", "url": self.link()}

    def __repr__(self):
        return f"GETRequest({self.url!r}, {self.parameters!r})"

class POSTRequest(Request):
    """Submit ``parameters`` (name -> value, sent as a form) to ``url``."""

    def __init__(self, url: str, parameters: dict):
        super().__init__(url)
        self.parameters = parameters

    def instruction(self) -> dict:
        return {"type": "POST", "url": self.url, "parameters": self.parameters}

    def __repr__(self):
        return f"POSTRequest({self.url!r}, {self.parameters!r})"

class FETCHRequest(Request):
    """
    Call an API from the current page with ``fetch()``. The tab does not navigate.

    Always a POST of ``parameters`` as the JSON body; the extension sets the
    headers. The request carries the page's cookies, so the tab must already be
    on the same origin as ``url``.

    The response never reaches a parser: the extension posts it to
    ``/fetch_result``, the server decodes the JSON and calls
    ``callback(json, request_data)``, which returns the next ``Request`` for
    this fetch (typically a ``GETRequest`` built from an id in the response),
    or ``None`` to let ``generate_request`` pick the next one. A failed fetch
    (non-2xx status or a body that is not JSON) skips the callback and also
    falls back to ``generate_request``.
    """

    def __init__(self, url: str, parameters: dict,
                 callback: Callable[[dict, "RequestData"], Request | None]):
        super().__init__(url)
        if not callable(callback):
            raise TypeError(f"callback is not callable: {callback!r}")
        self.parameters = parameters
        self.callback = callback

    def instruction(self) -> dict:
        return {"type": "FETCH", "url": self.url, "body": self.parameters}

    def __repr__(self):
        return f"FETCHRequest({self.url!r}, {self.parameters!r})"

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
        request: The ``Request`` the client is currently carrying out for this
            fetch, set by the server each time it hands one out (from
            ``generate_request`` or a ``FETCHRequest`` callback). The server
            reads a ``POSTRequest``'s form from it for the parser, and a
            ``FETCHRequest``'s callback when the response arrives.
        result: The ``Result`` of the last page returned for this fetch, set by
            the server before the ``update`` calls, so ``update`` /
            ``next_state`` / ``success`` can read its ``metadata`` and ``url``.
            ``None`` until a page has come back.

    Subclasses may attach their own attributes to a ``RequestData`` instance to
    carry state across the request parsing.
    """

    def __init__(self, requested_element: ScrapedElement, fetch_phase: Phase):
        self.requested_element = requested_element
        self.fetch_phase = fetch_phase
        self.request = None
        self.result = None

    def __repr__(self):
        return f"{self.requested_element=}, {self.fetch_phase}"

class BaseScraper:
    """
    Base class for a plugin's scraper - the object that decides what to keep and,
    in active mode, where to crawl next. Subclass it and override the hooks below.

    The server owns all crawl state (clients are stateless) and drives the scraper
    through ``POST /receive``. For each page a client posts, it calls, in order:

      * no token (the client navigated on its own)
          - ``unknown_page(result)``
      * token present (a page this scraper asked for came back)
          - ``update(element, request_data)`` once per parsed element
          - ``next_state(request_data)`` -> the request's new ``Phase``
          - ``success(request_data)`` iff that phase is ``DONE``
      * then, only if the client allows redirects (active mode)
          - ``generate_request(request_data)`` -> the next ``GETRequest`` / ``POSTRequest`` / ``FETCHRequest``

    What to override depends on the mode you chose:

      * Passive (the client leads, the server never redirects): override only
        ``unknown_page`` - save the elements you are shown and stop.
      * Active (the server leads the crawl): override ``update``, ``next_state``,
        ``generate_request`` (and ``success`` if you need a completion hook), plus
        usually ``unknown_page`` to seed the crawl from the first page.
    """

    def __init__(self, db: ScraperDatabase):
        """
        Args:
            db: The plugin's database instance (a ``ScraperDatabase`` subclass).
                It is the scraper's only persistence layer - call your own
                ``save_*`` / ``load_*`` helpers on it. The plugin's factory
                builds it, so a scraper that needs more than a path can take
                whatever else it likes alongside this argument.
        """
        self.db = db
        self.candidate_queue = []      # elements discovered but not yet fetched
        self.candidate_waiting = []     # elements currently being fetched
        self.special_request = False

    # We should maybe rename instead to something that says it was a page not explicitly requested
    def unknown_page(self, result: Result) -> None:
        """
        Handle a page the client navigated to on its own (no fetch token).

        The only hook a passive scraper needs: persist the elements and return.
        An active scraper may also find a uses to it.

        Args:
            result: The parsed page: ``result.elements``, the parser's
                ``result.metadata`` (may be ``None``) and ``result.url``, the
                address the client visited. Never ``None`` - a page that did
                not parse is skipped before this hook.
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

    def generate_request(self, request_data: RequestData = None) -> tuple[Request, RequestData] | tuple[None, None]:
        """
        Choose the next page for the client to fetch (active mode only).

        Called when the client allows redirects. Return ``(request, RequestData)``
        to fetch next, where ``request`` is a ``GETRequest(url, parameters)`` (query
        arguments, encoded into the url by the server), a ``POSTRequest(url, parameters)`` (a form) or a
        ``FETCHRequest(url, parameters, callback)`` (a JSON API call, no
        navigation; ``callback`` turns the response into the next request), or
        ``(None, None)`` to stop the crawl. Required for active scrapers.

        Args:
            request_data: The fetch that just completed, or ``None`` after a
                spontaneous page.

        Returns:
            A ``(request, request_data)`` pair, or ``(None, None)`` when finished.
        """
        raise NotImplementedError