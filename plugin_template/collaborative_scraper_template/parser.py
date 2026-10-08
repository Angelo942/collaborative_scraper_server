from urllib.parse import parse_qsl, urlsplit

import lxml.html

from collaborative_scraper.api import ScrapedElement, Result, RequestData, POSTRequest

class Page(ScrapedElement):
    """One received page. A real plugin defines one class per kind of item it extracts."""

    def __init__(self, path: str, title: str, get_parameters: dict, post_parameters: dict, size: int):
        super().__init__()
        self.path = path
        self.title = title
        self.get_parameters = get_parameters
        self.post_parameters = post_parameters
        self.size = size

    def __repr__(self):
        return f"Page({self.title!r}, path={self.path!r}, {self.size} chars)"

def extract_elements(html_page: str, url: str, request_data: RequestData | None) -> Result | None:
    """Turn a page into a Result. Return None if the page was not fully loaded.

    ``url`` is the full url of the page; ``request_data`` is the server's request
    this page answers, or None for a page the client navigated to on its own.
    """
    if not html_page:
        return None
    parts = urlsplit(url)
    get_parameters = dict(parse_qsl(parts.query, keep_blank_values=True))
    # Only a page the server asked the client to POST has a form to report.
    request = None if request_data is None else request_data.request
    post_parameters = request.parameters if isinstance(request, POSTRequest) else {}
    title = lxml.html.fromstring(html_page).findtext(".//title") or ""
    return Result([Page(parts.path, title.strip(), get_parameters, post_parameters, len(html_page))])
