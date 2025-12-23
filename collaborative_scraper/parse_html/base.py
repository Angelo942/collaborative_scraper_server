from __future__ import annotations

class ScrapedElement:
    def __init__(self):
        pass

    def __gt__(self, element: ScrapedElement):
        """ Define a metric of priority between two elements to parse """
        raise NotImplementedError

    # Is this required ?
    def __repr__(self):
        raise NotImplementedError

def extract_elements(html_page: str, path: str) -> list[ScrapedElement] | None:
    raise NotImplementedError
