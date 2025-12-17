from lxml import html
import json

def safe_int(value):
    try:
        return formatted_int(value)
    except ValueError:
        return 0

def formatted_int(value):
    return int(value.replace(",", "").replace(".", "").replace("_", ""))

class Article:
    def __init__(self, id=None, title=None, year=0, pdf=None, num_citing=-1, num_cited=-1, citing=None, cited=None, explored = False):
        self.id = id
        self.title = title
        self.year = year
        self.pdf = pdf
        self.num_citing = num_citing
        self.num_cited = num_cited
        self.citing = json.loads(citing) if isinstance(citing, str) else ([] if citing is None else citing)
        self.cited  = json.loads(cited)  if isinstance(cited, str)  else ([] if cited  is None else cited)
        self.explored = explored
    
    def load_from_page(self, node):
        raise NotImplemented

    def __gt__(self, article):
        return self.num_citing > article.num_citing

    def __repr__(self):
        return f"{self.title}(#{self.id}) [{len(self.cited)}({self.num_cited})/{len(self.citing)}({self.num_citing})]"

def load_page(path):
    with open(path, "r") as fd:
        page = html.fromstring(fd.read())
        return page

def extract_articles(path):
    raise NotImplemented

def get_papers_citing(article):
    raise NotImplemented

def get_papers_cited(article):
    raise NotImplemented
