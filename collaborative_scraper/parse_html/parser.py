import logging
from urllib.parse import urlparse
from collaborative_scraper.parse_html.base import ScrapedElement

logger = logging.getLogger(__name__)

# Map each site domain to its extractor (parse_html/extra/<project>/...).
# Example:
#   from collaborative_scraper.parse_html.extra.myproject.mysite import extract_elements as extract_from_mysite
supported_domains = {
    # "www.mysite.com": extract_from_mysite,
}

def extract_elements(payload: dict) -> list[ScrapedElement]:
    """ Must return None if the page was not fully loaded """
    meta = payload.get("meta", {})
    html_page = payload.get("html", "")
    url = meta.get("url", "")
    parsed = urlparse(url)
    domain = parsed.netloc
    parser_function = supported_domains[domain]
    try:
        articles = parser_function(html_page, parsed.path)
        if articles is None:
            with open("./debug_page.html", "w") as fd:
                fd.write(html_page)
            logger.error("Error extracting articles!")
        else:
            logger.debug("Extracted %d article(s) from %s", len(articles), parsed.netloc + parsed.path)
        return articles
    except Exception as e:
        with open("./debug_page.html", "w") as fd:
            fd.write(html_page)
        logger.error("Uncaught exception parsing page! %s", e)
