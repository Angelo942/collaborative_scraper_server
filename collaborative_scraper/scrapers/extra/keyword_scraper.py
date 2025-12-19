from collaborative_scraper.scrapers.extra.scopus_scraper import ScopusScraper, RequestData, Phase
from collaborative_scraper.parse_html.extra.scopus import ScopusArticle as Article

# TODO check that this is still working!!!

class KeywordScraper(ScopusScraper):
    def __init__(self, keywords: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords
    
    def find_next_article(self) -> Article:
        for article in self.new_articles:
            for keyword in self.keywords:
                if keyword in article.title.lower():
                    break
        else:
            article = max(self.new_articles)
        next_article = article
        self.new_articles.remove(next_article)
        return next_article

    def _update_impl(self, article: Article, request_data: RequestData) -> None:
        """Hook for subclasses to extend update behaviour."""
        if request_data is None:
            return
        # Don't save cited papers. The idea is that those are already the most important ones and you don't care about what they cite if it's not cited anymore anyway.
        if request_data.fetch_phase == Phase.CITING:
            if article not in self.new_articles and article.id not in self.explored:
                self.new_articles.append(article)
                self.explored.add(article.id)

class KeywordScraper(ScopusScraper):
    def __init__(self, keywords: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords
        self.current_keyword = None
        self.discovered = [] # Could use explored
        self.done = False
        self.second_scraper = None
        self.known_queries = self.db.get_queries()

    def _request_generator(self) -> str:
        yield from self.fetch_scopus_papers()
    
    def fetch_scopus_papers(self) -> str:
        for keyword in self.keywords:
            if keyword in self.known_queries:
                print(f"skipping query: {keyword}")
                for id in self.db.get_query_results(keyword):
                    self.discovered.append(self.known_articles[id])
                continue
            self.known_queries.append(keyword)
            self.current_keyword = []
            self.old_counter = 0
            while len(self.current_keyword) % 200 == 0:
                yield get_papers_from_keyword(keyword, len(self.current_keyword))
                if len(self.current_keyword) == self.old_counter:
                    print(f"found exactly {self.old_counter} papers")
                    break
                self.old_counter = len(self.current_keyword)
            self.db.save_query(keyword, self.current_keyword, "scopus")
        self.done = True

    def _update_impl(self, article: Article, request_data: RequestData) -> None:
        if self.current_keyword is None:
            return
        if article not in self.discovered:
            self.discovered.append(article)
        self.current_keyword.append(article.id)

    def next_target(self) -> tuple[str, RequestData]:
        for target in self.request_stream:
            request_data = RequestData(self.current_article, self.fetch_phase)
            return target, request_data
        if self.done:
            print("WE ARE DONE LOOKING FOR KEYWORDS")
            self.second_scraper = SeedScraper(*[article.id for article in self.discovered])
            self.second_scraper.known_articles = self.known_articles # Keep updating both at the same time
            self.done = False
        return self.second_scraper.next_target

    @property
    def fetch_phase(self) -> Phase:
        if self.second_scraper is None:
            return None
        else:
            return self.second_scraper.fetch_phase

    @property
    def current_article(self):
        if self.second_scraper is None:
            return None
        else:
            return self.second_scraper.current_article