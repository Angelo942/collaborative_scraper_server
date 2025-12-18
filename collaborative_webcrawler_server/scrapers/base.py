import logging

logger = logging.getLogger(__name__)

# To work in a distributed manner it must become partially stateless...
class BaseScraper:
    def __init__(self, db, blacklist = lambda article: False):
        self.db = db
        self.blacklist = blacklist # Allow to define rules to prevent exploring certain results
        self.known_articles = {article.id : article for article in self.db.get_articles()}
        self._current_article = None # Article currently being analysed by the scraper (find references and citations)
        self._fetch_phase = None # Store 
        self.request_stream = self._request_generator()
        self.candidate_queue = []
        self.special_request = False
        self.explored = set() # This is not optimal, but it is not possible to know if we explored an article who has zero citations so we need to store it somewhere to stop requesting them constantly
        
    def _request_generator(self):
        while True:
            # Handle requests from outside the scraping process
            paper_id = self.db.pop_next_fetch_request()
            if paper_id is not None:
                self.special_request = True
                self.current_article = self.known_articles[paper_id]
                logger.info("[SPECIAL REQUEST] %s", self.current_article)
            else:
                self.special_request = False
                self.current_article = self._pop_next_article()
                if self.current_article is None:
                    yield None
                    continue
                if self.blacklist(self.current_article):
                    logger.info("[blacklisted] %s", self.current_article)
                    continue
            yield from self._fetch_related_papers(self.current_article)

    def update(self, article, request_data={}):

        if self.special_request:
            return # We just needed to save this article, it's not part of the scraping process
        if article.id not in self.known_articles:
            self.db.save_page(article)
            self.known_articles[article.id] = article
        else:
            article = self.known_articles[article.id] # Make sure to work with a single object for each article

        self._update_impl(article, request_data) # user defined macro

        if request_data:
            requested_article = request_data["requested_article"]
            fetch_phase = request_data["fetch_phase"]
            if fetch_phase == "CITING" and article.id not in requested_article.citing: 
                requested_article.citing.append(article.id)
            elif fetch_phase == "CITED" and article.id not in requested_article.cited:
                requested_article.cited.append(article.id)

    def clear_references(self):
        for article in self.known_articles.values():
            for article_id in article.citing:
                if article_id not in self.known_articles:
                    article.citing = []
                    self.db.update_page(article)
                    break
            for article_id in article.cited:
                if article_id not in self.known_articles:
                    article.cited = []
                    self.db.update_page(article)
                    break

    # Can be overwritten 

    def _pop_next_article(self):
        if len(self.candidate_queue) != 0:
            next_article = max(self.candidate_queue)
            self.candidate_queue.remove(next_article)
        else:
            next_article = None
        return next_article

    def _update_impl(self, article, request_data):
        """Hook for subclasses to extend update behaviour."""
        if article not in self.candidate_queue and article.id not in self.explored:
            self.candidate_queue.append(article)
            self.explored.add(article.id)

    def success(self, request_data):
        """ When we receive a response and parsed all the articles in it """
        requested_article = request_data["requested_article"]
        fetch_phase = request_data["fetch_phase"]
        if fetch_phase == "CITING":
            # We may have new citations between when we saved the metadata and when we analysed all the papers
            if len(requested_article.citing) > requested_article.num_citing:
                logger.info("%s got more citations", requested_article)
                requested_article.num_citing = len(requested_article.citing)
            self.db.update_page(requested_article)
        if fetch_phase == "CITED":
            requested_article.num_cited = len(requested_article.cited)
            requested_article.explored = True # Not complete information, but at least it's an estimation
            self.db.update_page(requested_article)

    def next_target(self):
        while True:
            next_url = next(self.request_stream)
            if (self.fetch_phase == "CITING" and len(self.current_article.citing) == min(self.current_article.num_citing, 2000)): # There is a limit to 2000 papers on scopus
                logger.info(f"skipping papers citing {self.current_article}")
                for id in self.current_article.citing:
                    self.update(self.known_articles[id], {"fetch_phase": self.fetch_phase, "requested_article": self.current_article}) # Careful to not change the state before calling update
                self.fetch_phase = "SKIPPING"
            elif (self.fetch_phase == "CITED" and len(self.current_article.cited) == self.current_article.num_cited) and (self.current_article.num_cited % 200 != 0 or self.current_article.num_cited == 0): # Skip the ones we know are 0
                logger.info(f"skipping papers cited by {self.current_article}")
                for id in self.current_article.cited:
                    self.update(self.known_articles[id], {"fetch_phase": self.fetch_phase, "requested_article": self.current_article})
            else:
                break

        logger.debug(f"[{len(self.candidate_queue)}] exploring {self.fetch_phase} {self.current_article}")
        request_data = {"fetch_phase": self.fetch_phase, "requested_article": self.current_article}
        return next_url, request_data


    @property
    def current_article(self):
        return self._current_article

    @current_article.setter
    def current_article(self, value):
        self._current_article = value

    @property
    def fetch_phase(self):
        return self._fetch_phase

    @fetch_phase.setter
    def fetch_phase(self, value):
        self._fetch_phase = value
    # Must be overwritten

    def _fetch_related_papers(self, current_article):
        raise NotImplemented


    


