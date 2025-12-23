from __future__ import annotations
from collaborative_scraper.parse_html.base import ScrapedElement
import json

class Article(ScrapedElement):
    def __init__(self, id: int = None, title: str = None, year: int = 0, pdf: str = None, num_citing: int = -1, num_cited: int = -1, citing: list[int] | str = None, cited: list[int] | str = None, explored: bool = False):
        super().__init__()
        self.id = id
        self.title = title
        self.year = year
        self.pdf = pdf
        self.num_citing = num_citing
        self.num_cited = num_cited
        self.citing = json.loads(citing) if isinstance(citing, str) else ([] if citing is None else citing)
        self.cited  = json.loads(cited)  if isinstance(cited, str)  else ([] if cited  is None else cited)
        self.explored = explored

    def load_from_page(self, node:html.HtmlElement) -> bool:
        """ Extract the paper details from an html page. Return True on success """
        raise NotImplementedError

    def get_papers_citing(self) -> str:
        """ return the link to a page listing the articles citing a given article """
        raise NotImplementedError

    def get_papers_cited(self) -> str:
        """ return the link to a page listing the articles cited by a given article """
        raise NotImplementedError

    def __gt__(self, article: Article):
        return self.num_citing > article.num_citing

    def __repr__(self):
        return f"{self.title}(#{self.id}) [{len(self.cited)}({self.num_cited})/{len(self.citing)}({self.num_citing})]"
