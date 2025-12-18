from lxml import html
import json
import logging

logger = logging.getLogger(__name__)

def safe_int(value):
    try:
        return formatted_int(value)
    except ValueError:
        return 0

def formatted_int(value):
    return int(value.replace(",", "").replace(".", "").replace("_", ""))

def load_page(html_page):
    return html.fromstring(html_page)

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
        """ Extract the paper details from an html page """
        raise NotImplemented

    # This doesn't work unfortunately because on scopus we don't know immediately how many papers cited a given paper
    # @property
    # def explored(self):
    #     """ Did we download have all the informations about this article ? """
    #     if len(citing) > self.num_citing or (len(cited) > self.num_cited and not self.num_cited == 0):
    #       # this is wrong because we are gonna update the lists at each paper, but correct the number of articles only at the end of the process  
    #       logger.warning("%s contains corrupted info!", self)
    #     return len(cited) == self.num_cited and len(citing) == self.num_citing and self.num_cited != 0

    def __gt__(self, article):
        """ Define a metric of priority between two articles to parse """
        return self.num_citing > article.num_citing

    def __repr__(self):
        return f"{self.title}(#{self.id}) [{len(self.cited)}({self.num_cited})/{len(self.citing)}({self.num_citing})]"



def extract_articles(path):
    raise NotImplemented

def get_papers_citing(article):
    raise NotImplemented

def get_papers_cited(article):
    raise NotImplemented
