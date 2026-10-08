from __future__ import annotations

class ScrapedElement:
    """
    Base class for one item a parser pulls out of a page.

    A plugin subclasses this to hold the fields it wants to keep (title, url,
    ...) - the scraper and database work in terms of these objects. Subclasses
    define ``__repr__`` for logging.
    """

    def __init__(self):
        pass

    def __repr__(self):
        raise NotImplementedError

class Result:
    """
    Holds elements parsed from the page together with optional metadata describing
    the query.

    Needed for pages that describe the page parsed not through the url, but with
    elements that have to be extracted from the page itself. Example the Scopus
    result page that has the query parameters visible in the search window, but
    not the link anymore.

    ``url`` is the address of the parsed page. A parser leaves it unset: the
    server fills it in before handing the ``Result`` to the scraper.
    """

    def __init__(self, elements: list[ScrapedElement], metadata: dict = None):
        self.metadata = metadata
        self.elements = elements
        self.url: str | None = None

def extract_elements(html_page: str, url: str, request_data: RequestData | None) -> Result | None:
    """
    Parse a page into a ``Result`` - a plugin's parser entry point.

    Registered per host with ``reg.parser(host, fn)`` and called by the server
    for each page.
    ``url`` is the page's full url (scheme, host, path and query string): split it
    with ``urllib.parse`` to branch on the path or read the query arguments.
    ``request_data`` is the server-assigned fetch this page answers, or ``None``
    for a page the client navigated to on its own. ``request_data.request`` is
    the ``Request`` the client carried out: a ``POSTRequest``'s ``parameters`` are
    the form it submitted, and an ``ActionRequest`` means the page is the one the
    click left behind.

    Returns:
        The parsed elements in a ``Result``, or ``None`` if the page wasn't
        fully loaded - the contract every caller relies on to skip incomplete
        pages.
    """
    raise NotImplementedError
