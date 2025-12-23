import logging
from urllib.parse import urlparse
from collaborative_scraper.parse_html.base import ScrapedElement
from collaborative_scraper.parse_html.extra.scopus import extract_elements as extract_articles_from_scopus
from collaborative_scraper.parse_html.extra.webofscience import extract_elements as extract_articles_from_webofscience
from collaborative_scraper.parse_html.extra.sciencedirect import extract_elements as extract_article_info_from_sciencedirect
from collaborative_scraper.parse_html.extra.saxo import extract_elements as extract_portfolio_info

logger = logging.getLogger(__name__)

supported_domains = {
    "www.sciencedirect.com": extract_article_info_from_sciencedirect,
    "www.webofscience.com": extract_articles_from_webofscience,
    "www.scopus.com": extract_articles_from_scopus,
    "www.saxoinvestor.com": extract_portfolio_info,
}

def extract_elements(payload: dict) -> list[ScrapedElement]:
    """ Must return None if the page was not fully loaded """
    meta = payload.get("meta", {})
    html_page = payload.get("html", "")
    url = meta.get("url", "")
    parsed = urlparse(url)
    domain = parsed.netloc
    parser_function = supported_domains[domain]
    articles = parser_function(html_page, parsed.path)
    if articles is None:
        with open("./debug_page.html", "w") as fd:
            fd.write(html_page)
        logger.error("Error extracting articles!")
    else:
        logger.debug("Extracted %d article(s) from %s", len(articles), parsed.netloc + parsed.path)
    return articles
