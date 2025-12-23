from __future__ import annotations
from collaborative_scraper.parse_html.extra.science_article import Article
import logging
import re
from collaborative_scraper.utils import save_snapshot, Path
from lxml import html
from collaborative_scraper.utils import formatted_int, safe_int

logger = logging.getLogger(__name__)

class ScopusArticle(Article):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_from_result_page(self, node: html.HtmlElement) -> bool:
        try:
            title = node.xpath("td[2]/div/div/h3/a")[0]
        except IndexError:
            return False
        self.title = title.text_content()
        self.link = "https://www.scopus.com" + title.attrib["href"]
        self.id = int(self.link.split("?")[0].split("/")[-1]) # publications/85096958755?origin=...
        
        self.pdf = f"https://www.scopus.com/pages/publications/{self.id:010d}"
        self.year = int(node.xpath("td[5]/div/span")[0].text_content())

        try:
            self.num_citing = formatted_int(node.xpath("td[6]/div/a")[0].text_content()) # div/a is there only if there is also a link, so if there are at least 1 citation
        except IndexError:
            self.num_citing = 0
        self.num_cited = -1
        return True
    
    def load_from_article_page(self, page: html.HtmlElement) -> bool:
        tile_section = page.xpath("/html/body/div/div/main/div/section/article/div[1]/div[3]/div[1]/h2/span")[0]
        self.title = tile_section.text_content()

        # id already set by the caller

        # header_section = page.xpath("/html/body/div/div/main/div/section/article/div[1]/div[3]/div[2]/div/div")[0]
        # header_text = header_section.text_content()
        doi_section = page.xpath("/html/body/div/div/main/div/section/article/div[1]/div[3]/div[2]/div/div/div/span")[0]
        doi_string = doi_section.text_content()
        #'DOI: 10.1080/0951192X.2016.1268269'
        assert doi_string.startswith("DOI: ")
        self.doi = re.search(r'DOI: (\S+)', doi_string, re.IGNORECASE).group(1)
        # self.doi = re.search(r'DOI: (\S+)Copy', header_text, re.IGNORECASE).group(1)
        self.link = "doi.org/" + self.doi

        year_section = page.xpath("/html/body/div/div/main/div/section/article/div[1]/div[3]/div[2]/div/div/span[2]")[0]
        self.year = int(year_section.text_content())
        
        # self.year = int(re.search(r'(\d{4})', header_text, re.IGNORECASE).group(1))
        # self.year = int(re.search(r'([12]\d{3})', header_text, re.IGNORECASE).group(1))
        # self.year = int(re.search(r'((?:19|20)\d{2})', header_text, re.IGNORECASE).group(1))

        citing_section = page.xpath("/html/body/div/div/main/div/section/article/div[2]/div/div/div[1]/button[3]/span")[0]
        citing_string = citing_section.text_content()
        self.num_citing = int(re.search(r'\((\S+)\)', citing_string, re.IGNORECASE).group(1))

        cited_section = page.xpath("/html/body/div/div/main/div/section/article/div[2]/div/div/div[1]/button[4]/span")[0]
        cited_string = cited_section.text_content()
        self.num_cited = int(re.search(r'\((\S+)\)', cited_string, re.IGNORECASE).group(1))

    # TODO handle explored in the scrapers
    # This doesn't work unfortunately because on scopus we don't know immediately how many papers cited a given paper
    # @property
    # def explored(self):
    #     """ Did we download have all the informations about this article ? """
    #     if not self._explored:
    #         if len(self.citing) > self.num_citing or (len(self.cited) > self.num_cited and not self.num_cited == 0):
    #         # this is wrong because we are gonna update the lists at each paper, but correct the number of articles only at the end of the process  
    #             logger.warning("%s contains corrupted info!", self)
    #         self._explored = len(self.cited) == self.num_cited and len(self.citing) == self.num_citing and self.num_cited % 200 != 0: # I accept that if I have exactly 200 papers I won't detect that we finished exploring it
    #     return self._explored

def extract_articles_from_results(html_page: str) -> list[Article] | None:
    page = html.fromstring(html_page)
    articles = []

    # If message No article match is visible return []
    comment = page.xpath("/html/body/div[1]/div/div[1]/div/div/div[3]/micro-ui/document-search-results-page/div[1]/section[2]/div/div[2]/div/div[1]")[0]
    if comment.attrib["style"] == "display: block;": # != 'display: none;':
        return articles

    try:
        num_articles = formatted_int(page.xpath("/html/body/div[1]/div/div[1]/div/div/div[3]/micro-ui/document-search-results-page/div[1]/section[1]/div[3]/div/div/div[1]/h2")[0].text_content().split()[0])
    except IndexError:
        logger.error("IndexError -> Page didn't load")
        return None # this mean that the page didn't load properly

    num_articles -= (num_articles // 200) * 200
    elements = page.xpath("/html/body/div[1]/div/div[1]/div/div/div[3]/micro-ui/document-search-results-page/div[1]/section[2]/div/div[2]/div/div[2]/div/div[2]/div[1]/table/tbody/tr")
    # for i, element in enumerate(elements[1::3]):
    i = 1
    while i < len(elements):
        element = elements[i]
        
        article = ScopusArticle()
        # Sometimes we have an empty line out of nowhere...
        if not article.load_from_result_page(element):
            logger.debug(f"skipping line {element.text_content()}")
            i += 1
            continue
        # print(article)
        if article.id is not None:
            articles.append(article)
        i += 3

    if len(articles) not in [num_articles, 200]:
        raise Exception("Missing articles -> Make sure to set max number per page.")
    return articles

def extract_article_info_from_page(html_page: str, path: str) -> Article:
    page = html.fromstring(html_page)
    id = int(path.split("/")[-1])
    article = ScopusArticle(id=id)
    article.load_from_article_page(page)
    return article

def extract_elements(html_page: str, path: str) -> list[Article]:
    if path.startswith("/results"):
        return extract_articles_from_results(html_page)
    elif path.startswith("/pages"):
        return [extract_article_info_from_page(html_page, path)]
    else:
        logger.warning("page %s is not handled on scopus!", path)
        return []

def get_papers_citing(article: Article, offset: int = 0) -> str: # the settings are not respected, so careful
    if offset:
        return f"https://www.scopus.com/results/results.uri?s=ref%282-s2.0-{article.id:010d}%29&sot=cite&sdt=a&origin=resultslist&src=s&sort=cp-f&limit=200&offset={offset}"
    return f"https://www.scopus.com/results/results.uri?s=ref%282-s2.0-{article.id:010d}%29&sot=cite&sdt=a&origin=resultslist&src=s&sort=cp-f&limit=200"

def get_papers_cited(article: Article, offset: int = 0) -> str:
    if offset:
        return f"https://www.scopus.com/results/results.uri?s=CITEID({article.id:010d})&sot=record&sdt=references&origin=recordpage&src=s&sort=cp-f&limit=200&offset={offset}"
    return f"https://www.scopus.com/results/results.uri?s=CITEID({article.id:010d})&sot=record&sdt=references&origin=recordpage&src=s&sort=cp-f&limit=200"

def get_papers_from_keyword(keyword: str, offset: int = 0) -> str:
    if offset:
        return f"https://www.scopus.com/results/results.uri?s=TITLE-ABS-KEY%28{keyword}%29&limit=200&origin=searchbasic&sort=cp-f&src=s&sot=b&sdt=b&offset={offset}"
    return f"https://www.scopus.com/results/results.uri?s=TITLE-ABS-KEY%28{keyword}%29&limit=200&origin=searchbasic&sort=cp-f&src=s&sot=b&sdt=b"