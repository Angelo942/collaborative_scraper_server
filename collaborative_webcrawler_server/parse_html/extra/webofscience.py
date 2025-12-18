from collaborative_webcrawler_server.parse_html.base import *

class Webofscience_Article(Article):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) 
   
    def load_from_page(self, node):
        title = node.xpath("div/div/div[2]/div[2]/app-summary-title/h3/a")[0]
        self.title = title.text_content()
        self.link = "https://www.webofscience.com" + title.attrib["href"]
        self.id = int(self.link.split(":")[-1]) # WOS:001487367400001

        self.year = int(node.xpath("div/div/div[2]/div[2]/div[1]/span[1]")[0].text_content().split(" ")[-1])

        try:
            self.pdf = node.xpath("div/div/div[2]/div[3]/app-summary-record-links/a[2]")[0].attrib["href"]
        except IndexError:
            self.pdf = None

        try:
            self.num_citing = safe_int(node.xpath("div/div/div[4]/div/div[1]/div[2]/a")[0].text_content())
            self.num_cited = safe_int(node.xpath("div/div/div[4]/div/div[1]/div[1]/a")[0].text_content())
        except IndexError:
            try:
                self.num_citing = safe_int(node.xpath("div/div/div[4]/div/div[1]/div[1]/a")[0].text_content())
            except IndexError:
                self.num_citing = 0
            self.num_cited = 0

def extract_articles(path):
    articles = []
    page = load_page(path)
    for i, element in enumerate(page.xpath("/html/body/app-wos/main/div/div/div[2]/div/div/div[2]/app-input-route/app-base-summary-component/div/div[2]/app-records-list/app-record")):
        # print(i)
        article = Article()
        try:
            article.load_from_page(element)
            # print(article)
            if article.id is not None:
                articles.append(article)
        except:
            pass
    return articles

def get_papers_citing(article):
    return f"https://www.webofscience.com/wos/woscc/citing-summary/WOS:{article.id}?from=woscc&type=colluid&eventMode=timeCitedOnSummary"

def get_papers_cited(article):
    return f"https://www.webofscience.com/wos/woscc/cited-references-summary/WOS:{article.id}?type=colluid&from=woscc"