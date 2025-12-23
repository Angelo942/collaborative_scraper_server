from collaborative_scraper.scrapers.extra.scopus_scraper import ScopusScraper, RequestData, Phase
from collaborative_scraper.parse_html.extra.scopus import ScopusArticle as Article
import logging

logger = logging.getLogger(__name__)

class SeedScraper(ScopusScraper):
    def __init__(self, *seeds, **kwargs):
        super().__init__(**kwargs)
        self.current_layer = [self.known_articles[seed] for seed in seeds]
        self.size_layer = len(self.current_layer)
        self.explored = {id for id in seeds}
        self.next_layer = set()

    def _pop_next_article(self) -> Article | None:
        if len(self.current_layer) == 0 and len(self.candidate_waiting) == 0:
            self.current_layer = self.next_layer
            self.size_layer = len(self.current_layer)
            self.next_layer = set()

        if len(self.current_layer):
            next_article = max(self.current_layer)
            self.current_layer.remove(next_article)
            self.candidate_waiting.append(next_article)
            return next_article
        else:
            logger.warning("We don't have anything left to explore!")
            return None
                    
    def _update_impl(self, article: Article, request_data: RequestData) -> None:
        if request_data is None:
            return
        # Don't save cited papers. The idea is that the papers we have are already the most important ones and you don't care about what they cite if it's not cited anymore anyway.
        if request_data.fetch_phase == Phase.CITING:
            if article not in self.next_layer and article.id not in self.explored and article.num_citing >= 5:
                self.next_layer.add(article)
                self.explored.add(article.id)