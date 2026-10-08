from collaborative_scraper.api import Registrar

from collaborative_scraper_template.parser import extract_elements
from collaborative_scraper_template.scraper import PrintScraper

def register(reg: Registrar) -> None:
    """Called once by the core at startup. Declares everything this plugin provides."""
    reg.project("template")                 # owns the "template:" namespace and its project folder
    reg.parser("*", extract_elements)       # any url; or "site.com", "www.site.com", "www.site.com/page"
    reg.scraper("debug", _debug_scraper)    # target "template:debug"

def _debug_scraper(cfg: dict) -> PrintScraper:
    """Factory: called with the target's [targets."template:debug"] config table.

    ``cfg["db_file"]`` is the resolved database path inside the project folder.
    This template stores nothing, so it is unused; a real plugin opens its
    ``ScraperDatabase`` subclass here and passes it to the scraper.
    """
    return PrintScraper(None)
