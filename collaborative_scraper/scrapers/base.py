from enum import Enum, auto
from collections.abc import Callable
from collaborative_scraper.parse_html.base import Article
import logging

logger = logging.getLogger(__name__)

class Phase(Enum):
    CITING = auto()
    CITED = auto()
    SKIPPING = auto()

class RequestData:
    def __init__(self, requested_article: Article, fetch_phase: Phase):
        self.requested_article = requested_article
        self.fetch_phase = fetch_phase

# To work in a distributed manner it must become partially stateless...
class BaseScraper:
    def __init__(self, db, blacklist: Callable[[Article], bool] = lambda article: False):
        self.db = db
        self.blacklist = blacklist # Allow to define rules to prevent exploring certain results
        self.known_articles = {article.id : article for article in self.db.get_articles()}
        self._current_article = None # Article currently being analysed by the scraper (find references and citations)
        self._fetch_phase = None # Store 
        self.request_stream = self._request_generator()
        self.candidate_queue = []
        self.special_request = False
        self.explored = set() # This is not optimal, but it is not possible to know if we explored an article who has zero citations so we need to store it somewhere to stop requesting them constantly
        
    def _request_generator(self) -> str:
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

    def update(self, article: Article, request_data: RequestData = None) -> None:

        if self.special_request:
            return # We just needed to save this article, it's not part of the scraping process
        if article.id not in self.known_articles:
            self.db.save_page(article)
            self.known_articles[article.id] = article
        else:
            article = self.known_articles[article.id] # Make sure to work with a single object for each article

        self._update_impl(article, request_data) # user defined macro

        if request_data is not None:
            if request_data.fetch_phase == Phase.CITING and article.id not in request_data.requested_article.citing: 
                request_data.requested_article.citing.append(article.id)
            elif request_data.fetch_phase == Phase.CITED and article.id not in request_data.requested_article.cited:
                request_data.requested_article.cited.append(article.id)

    def clear_references(self, article: Article = None):
        if article is None:
            articles_to_clean = self.known_articles.values()
        else:
            articles_to_clean = [article]
        for article in articles_to_clean:
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

    def _pop_next_article(self) -> Article | None:
        if len(self.candidate_queue) != 0:
            next_article = max(self.candidate_queue)
            self.candidate_queue.remove(next_article)
        else:
            next_article = None
        return next_article

    def _update_impl(self, article: Article, request_data: RequestData) -> None:
        """Hook for subclasses to extend update behaviour."""
        if article not in self.candidate_queue and article.id not in self.explored:
            self.candidate_queue.append(article)
            self.explored.add(article.id)

    def success(self, request_data: RequestData) -> None:
        """ When we receive a response and parsed all the articles in it """
        if request_data.fetch_phase == Phase.CITING:
            # We may have new citations between when we saved the metadata and when we analysed all the papers
            if len(request_data.requested_article.citing) > request_data.requested_article.num_citing:
                logger.info("%s got more citations", request_data.requested_article)
                request_data.requested_article.num_citing = len(request_data.requested_article.citing)
            self.db.update_page(request_data.requested_article)
        if request_data.fetch_phase == Phase.CITED:
            request_data.requested_article.num_cited = len(request_data.requested_article.cited)
            request_data.requested_article.explored = True # Not complete information, but at least it's an estimation
            self.db.update_page(request_data.requested_article)

    def next_target(self) -> tuple[str, RequestData]:
        while True:
            next_url = next(self.request_stream)
            if (self.fetch_phase == Phase.CITING and len(self.current_article.citing) == min(self.current_article.num_citing, 2000)): # There is a limit to 2000 papers on scopus
                logger.info(f"skipping papers citing {self.current_article}")
                for id in self.current_article.citing:
                    if id not in self.known_articles:
                        logger.error("articles got corrupted: clearing unknown articles")
                        self.clear_references(self.current_article)
                        break
                    else:
                        self._update_impl(self.known_articles[id], RequestData(self.current_article, self.fetch_phase)) # Careful to not change the state before calling update
                self.fetch_phase = Phase.SKIPPING
            elif (self.fetch_phase == Phase.CITED and len(self.current_article.cited) == self.current_article.num_cited) and (self.current_article.num_cited % 200 != 0 or self.current_article.num_cited == 0): # Skip the ones we know are 0
                logger.info(f"skipping papers cited by {self.current_article}")
                for id in self.current_article.cited:
                    if id not in self.known_articles:
                        logger.error("articles got corrupted: clearing unknown articles")
                        self.clear_references(self.current_article)
                        break
                    else:
                        self._update_impl(self.known_articles[id], RequestData(self.current_article, self.fetch_phase))
            else:
                break

        logger.debug(f"[{len(self.candidate_queue)}] exploring {self.fetch_phase} {self.current_article}")
        request_data = RequestData(self.current_article, self.fetch_phase)
        return next_url, request_data

    @property
    def current_article(self) -> Article:
        return self._current_article

    @current_article.setter
    def current_article(self, value: Article):
        self._current_article = value

    @property
    def fetch_phase(self) -> Phase:
        return self._fetch_phase

    @fetch_phase.setter
    def fetch_phase(self, value: str):
        self._fetch_phase = value
    # Must be overwritten

    def _fetch_related_papers(self, current_article: Article) -> str:
        raise NotImplemented