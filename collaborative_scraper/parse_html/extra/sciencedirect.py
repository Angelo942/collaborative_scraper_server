from collaborative_scraper.parse_html.base import *

class Sciencedirect_Article(Article):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def load_from_page(self, node: html.HtmlElement) -> bool:
        title = node.xpath("//*[@id='screen-reader-main-title']")[0]
        self.title = title.xpath("span")[0].text_content()

        self.link = node.xpath("//*[@id='article-identifier-links']/a/span/span")[0].text_content()
        scopus_link = node.xpath("//*[@id='citing-articles-view-all-btn']")[0].attrib["href"]
        self.id = int(scopus_link.split("s2.0-")[-1].split("&")[0])
        
        self.year = int(title.xpath("div/span")[0].text_content().split()[0])

        citing = node.xpath("//*[@id='citing-articles-header']/h2")[0].text_content()
        self.num_citing = safe_int(citing.split("(")[-1].split(")")[0])

        self.num_cited = len(node.xpath("//*[@id='reference-links-aep-bibliography-sec-id71']/li"))

        return True

def extract_article_info(html_page: str) -> Article:
    page = load_page(html_page)
    article = Sciencedirect_Article()
    article.load_from_page(page)
    return article

def extract_articles(html_page: str, path: str) -> list[Article] | None:
    return [extract_article_info(html_page)]