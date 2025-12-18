from collaborative_webcrawler_server.scrapers.extra.scopus_scraper import ScopusScraper as Scraper

class PopularScraper(Scraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_articles = [self.known_articles[id] for id in self.db.get_unexplored()]
        size_layer = len(self.new_articles)

    def _pop_next_article(self):
        next_article = max(self.new_articles)
        self.new_articles.remove(next_article)
        self.size_layer = len(self.current_layer)
        return next_article
        
    def _update_impl(self, article, request_data):
        if article not in self.new_articles and article.id not in self.explored:
            self.new_articles.append(article)
            self.explored.add(article.id)