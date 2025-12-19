from collaborative_scraper.parse_html.base import *
import logging

logger = logging.getLogger(__name__)

class ScopusArticle(Article):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_from_page(self, node: html.HtmlElement) -> None:
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

def extract_articles(html_page: str) -> list[Article]:
    page = load_page(html_page)
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
        
        # print(i)
        article = ScopusArticle()
        # print(element.text_content())
        # Sometimes we have an empty line out of nowhere...
        if not article.load_from_page(element):
            print(f"skipping line {element.text_content()}")
            i += 1
            continue
        # print(article)
        if article.id is not None:
            articles.append(article)
        i += 3

    if len(articles) not in [num_articles, 200]:
        raise Exception("Missing articles -> Make sure to set max number per page.")
    return articles

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