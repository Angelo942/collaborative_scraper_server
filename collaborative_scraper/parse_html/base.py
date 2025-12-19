from __future__ import annotations
from lxml import html
import json
import logging

logger = logging.getLogger(__name__)

def safe_int(value: str) -> int:
    try:
        return formatted_int(value)
    except ValueError:
        return 0

def formatted_int(value: str) -> int:
    return int(value.replace(",", "").replace(".", "").replace("_", ""))

def load_page(html_page: str) -> html.HtmlElement:
    return html.fromstring(html_page)

class Article:
    def __init__(self, id: int = None, title: str = None, year: int = 0, pdf: str = None, num_citing: int = -1, num_cited: int = -1, citing: list[int] | str = None, cited: list[int] | str = None, explored: bool = False):
        self.id = id
        self.title = title
        self.year = year
        self.pdf = pdf
        self.num_citing = num_citing
        self.num_cited = num_cited
        self.citing = json.loads(citing) if isinstance(citing, str) else ([] if citing is None else citing)
        self.cited  = json.loads(cited)  if isinstance(cited, str)  else ([] if cited  is None else cited)
        self._explored = explored
    
    def load_from_page(self, node:html.HtmlElement) -> bool:
        """ Extract the paper details from an html page """
        raise NotImplemented

    @property
    def explored(self) -> bool:
        return self._explored

    @explored.setter
    def explored(self, value: bool):
        self._explored = value

    def __gt__(self, article: Article):
        """ Define a metric of priority between two articles to parse """
        return self.num_citing > article.num_citing

    def __repr__(self):
        return f"{self.title}(#{self.id}) [{len(self.cited)}({self.num_cited})/{len(self.citing)}({self.num_citing})]"



def extract_articles(html_page: str, path: str) -> list[Article] | None:
    raise NotImplemented

def get_papers_citing(article: Article) -> str:
    raise NotImplemented

def get_papers_cited(article: Article) -> str:
    raise NotImplemented
