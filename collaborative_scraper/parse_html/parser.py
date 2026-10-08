import logging
from fnmatch import fnmatchcase
from urllib.parse import urlparse

from collaborative_scraper.parse_html.base import Result
from collaborative_scraper.registry import get_registry
from collaborative_scraper.scrapers.base import RequestData

logger = logging.getLogger(__name__)

def supported_domains() -> dict:
    """url pattern -> parser, as declared by the installed plugins."""
    return get_registry().parsers

def best_match(patterns, url: str) -> str | None:
    """The most specific glob in ``patterns`` matching ``url``, or None.

    A pattern is an ``fnmatch`` glob over the host (``www.site.com``, ``*.site.com``,
    ``*``) or, when it has a ``/``, over host + path (``www.site.com/page*``). The
    one with the most characters besides ``*`` wins.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    page = host + parsed.path
    matches = [p for p in patterns if fnmatchcase(page if "/" in p else host, p)]
    return max(matches, key=lambda p: (len(p) - p.count("*"), p), default=None)

def extract_elements(html_page: str, url: str, request_data: RequestData | None = None) -> Result | None:
    """ Must return None if the page was not fully loaded """

    domains = supported_domains()
    pattern = best_match(domains, url)
    if pattern is None:
        # Not an error the client can do anything about: it visited a page no
        # installed plugin parses. Say which patterns *are* parsed, so a missing
        # or half-loaded plugin is obvious from the log line alone.
        logger.warning("%s is not in the supported domains: %s",
                       url, sorted(domains) or "none (no plugin installed)")
        return None
    result = domains[pattern](html_page, url, request_data)
    if result is None or isinstance(result, Result):
        return result
    raise TypeError(f"parser for {pattern!r} returned {type(result).__name__}, "
                    f"expected Result or None")
