import logging
from urllib.parse import urlparse

from collaborative_scraper.parse_html.base import ScrapedElement
from collaborative_scraper.registry import get_registry

logger = logging.getLogger(__name__)

def supported_domains() -> dict:
    """host -> parser, as declared by the installed plugins."""
    return get_registry().parsers

def extract_elements(html_page: str, url: str) -> list[ScrapedElement] | None:
    """ Must return None if the page was not fully loaded """

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    domains = supported_domains()
    parser_function = domains.get(domain)
    if parser_function is None:
        # Not an error the client can do anything about: it visited a page no
        # installed plugin parses. Say which hosts *are* parsed, so a missing
        # or half-loaded plugin is obvious from the log line alone.
        logger.warning("%s is not in the supported domains: %s",
                       domain or url, sorted(domains) or "none (no plugin installed)")
        return None
    return parser_function(html_page, parsed.path)
