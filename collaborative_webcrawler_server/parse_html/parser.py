import logging
from collaborative_webcrawler_server.parse_html.extra.scopus import extract_articles as extract_articles_from_scopus
from collaborative_webcrawler_server.parse_html.extra.webofscience import extract_articles as extract_articles_from_webofscience
from collaborative_webcrawler_server.parse_html.extra.sciencedirect import extract_articles as extract_article_info_from_sciencedirect

logger = logging.getLogger(__name__)

supported_domains = {
    "www.sciencedirect.com": extract_article_info_from_sciencedirect,
    "www.webofscience.com": extract_articles_from_webofscience,
    "www.scopus.com": extract_articles_from_scopus
}

def extract_articles(payload):
    """ Must return None if the page was not fully loaded """
    meta = payload.get("meta", {})
    html_page = payload.get("html", "")
    domain = meta.get("domain", "unknown")
    parser_function = supported_domains[domain]
    articles = parser_function(html_page)
    logger.debug(f"[PARSE] Extracted %d article(s) from %s", len(articles), meta.get('url'))
    return articles