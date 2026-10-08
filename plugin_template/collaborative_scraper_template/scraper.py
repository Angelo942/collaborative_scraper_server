from collaborative_scraper.api import BaseScraper, Result

class PrintScraper(BaseScraper):
    """Passive scraper: prints every page the client sends and never redirects it."""

    def unknown_page(self, result: Result) -> None:
        """A page the client navigated to on its own."""
        print(f"received {result.url}")
        for page in result.elements:
            print(f"  title: {page.title!r}")
            print(f"  path: {page.path}  size: {page.size} chars")
            if page.get_parameters:
                print(f"  get parameters: {page.get_parameters}")

    def generate_request(self, request_data=None):
        """Called when the client allows redirects: (None, None) means nothing to fetch."""
        return None, None
