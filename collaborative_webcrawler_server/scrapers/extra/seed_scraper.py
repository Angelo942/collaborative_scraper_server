from collaborative_webcrawler_server.scrapers.extra.scopus_scraper import ScopusScraper as Scraper
import logging

logger = logging.getLogger(__name__)

class SeedScraper(Scraper):
    def __init__(self, *seeds, **kwargs):
        super().__init__(**kwargs)
        self.current_layer = [self.known_articles[seed] for seed in seeds]
        print(self.current_layer)
        self.size_layer = len(self.current_layer)
        self.explored = {id for id in seeds}
        self.next_layer = set()

    def _pop_next_article(self):
        if len(self.current_layer) == 0:# or max(self.current_layer).num_citing < 1:
            self.current_layer = self.next_layer
            self.size_layer = len(self.current_layer)
            self.next_layer = set()

        if len(self.current_layer):
            next_article = max(self.current_layer)
            self.current_layer.remove(next_article)
            # next_article = self.current_layer.pop() # Take a random element to go faster
            return next_article
        else:
            logger.warning("We don't have anything left to explore!")
            return None
                    
    def _update_impl(self, article, request_data):
        fetch_phase = request_data.get("fetch_phase")
        # Don't save cited papers. The idea is that the papers we have are already the most important ones and you don't care about what they cite if it's not cited anymore anyway.
        if fetch_phase == "CITING":
            if article not in self.next_layer and article.id not in self.explored and article.num_citing >= 5:
                self.next_layer.add(article)
                self.explored.add(article.id)