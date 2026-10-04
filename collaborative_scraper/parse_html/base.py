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

def extract_elements(html_page: str, path: str, get_parameters: dict,
                     post_parameters: dict) -> Result | None:
    """
    Parse a page into a ``Result`` - a plugin's parser entry point.

    Registered per host with ``reg.parser(host, fn)`` and called by the server
    for each page.
    Branch on ``path`` and the parameters the page was requested with to parse
    different page types of the same site: ``get_parameters`` comes from the
    url's query string, ``post_parameters`` from the form the client submitted
    (empty for a GET). Both map a name to a single value.

    Returns:
        The parsed elements in a ``Result``, or ``None`` if the page wasn't
        fully loaded - the contract every caller relies on to skip incomplete
        pages.
    """
    raise NotImplementedError
