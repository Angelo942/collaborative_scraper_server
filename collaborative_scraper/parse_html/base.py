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

def extract_elements(html_page: str, path: str) -> list[ScrapedElement] | None:
    """
    Parse a page into a list of ``ScrapedElement`` - a plugin's parser entry point.

    Registered per host with ``reg.parser(host, fn)`` and called by the server
    for each page.
    Branch on ``path`` to parse different page types of the same site.

    Returns:
        The parsed elements, or ``None`` if the page wasn't fully loaded - the
        contract every caller relies on to skip incomplete pages.
    """
    raise NotImplementedError
