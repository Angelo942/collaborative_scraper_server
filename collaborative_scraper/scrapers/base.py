from enum import Enum, auto
from collections.abc import Callable
from collaborative_scraper.parse_html.base import ScrapedElement
import logging

logger = logging.getLogger(__name__)

class Phase(Enum):
    CITING = auto()
    CITED = auto()
    SKIPPING = auto()

class RequestData:
    def __init__(self, requested_article: ScrapedElement, fetch_phase: Phase):
        self.requested_article = requested_article
        self.fetch_phase = fetch_phase

# To work in a distributed manner it must become partially stateless...
class BaseScraper:
    def __init__(self, db, blacklist: Callable[[ScrapedElement], bool] = lambda element: False):
        self.db = db
        self.blacklist = blacklist # Allow to define rules to prevent exploring certain results
        self._current_article = None # ScrapedElement currently being analysed by the scraper (find references and citations)
        self._fetch_phase = None
        self.request_stream = self._request_generator()
        self.candidate_queue = []
        self.special_request = False
        self.explored = set() # This is not optimal, but it is not possible to know if we explored an article who has zero citations so we need to store it somewhere to stop requesting them constantly
        
    def _request_generator(self) -> str:
        """
        Infinite generator yielding URLs to fetch.

        Include bypass of normal logic to query specific articles specified in the database.

        Yields:
            str | None: URL to fetch, or None if no article are needed.
        """
        while True:
            # Handle requests from outside the scraping process
            paper_id = self.db.pop_next_fetch_request()
            if paper_id is not None:
                self.special_request = True
                self.current_element = self.known_articles[paper_id]
                logger.info("[SPECIAL REQUEST] %s", self.current_element)
            else:
                self.special_request = False
                self.current_element = self._pop_next_article()
                if self.current_element is None:
                    yield None
                    continue
                if self.blacklist(self.current_element):
                    logger.info("[blacklisted] %s", self.current_element)
                    continue
            yield from self._fetch_related_papers(self.current_element)

    def update(self, article: ScrapedElement, request_data: RequestData = None) -> None:
        """
        Update internal state given a discovered article.

        Args:
            article: Parsed article to integrate.
            request_data (optional):
                Context describing which request triggered this update.
        """
        # if self.special_request:
        #     return # We just needed to save this article, it's not part of the scraping process
        if article.id not in self.known_articles:
            self.db.save_element(article)
            self.known_articles[article.id] = article
        else:
            article = self.known_articles[article.id] # Make sure to work with a single object for each article

        self._update_impl(article, request_data) # user defined macro

        if request_data is not None:
            if request_data.fetch_phase == Phase.CITING and article.id not in request_data.requested_article.citing: 
                request_data.requested_article.citing.append(article.id)
            elif request_data.fetch_phase == Phase.CITED and article.id not in request_data.requested_article.cited:
                request_data.requested_article.cited.append(article.id)

    def clear_references(self, article: ScrapedElement = None):
        """
        Util method to remove corrupted citation and reference links.

        Args:
            article (optional):
                Specific article to clean. If None, all known articles are checked.
        """
        if article is None:
            articles_to_clean = self.known_articles.values()
        else:
            articles_to_clean = [article]
        for article in articles_to_clean:
            for article_id in article.citing:
                if article_id not in self.known_articles:
                    article.citing = []
                    self.db.update_element(article)
                    break
            for article_id in article.cited:
                if article_id not in self.known_articles:
                    article.cited = []
                    self.db.update_element(article)
                    break

    # Can be overwritten 

    def _pop_next_article(self) -> ScrapedElement | None:
        """
        Select the next article to explore from the candidate queue.

        ScrapedElements are prioritized using their __gt__ implementation.

        Returns:
            ScrapedElement | None: Selected article, or None if the queue is empty.
        """
        if len(self.candidate_queue) != 0:
            next_article = max(self.candidate_queue)
            self.candidate_queue.remove(next_article)
        else:
            next_article = None
        return next_article

    def _update_impl(self, article: ScrapedElement, request_data: RequestData) -> None:
        """
        Hook for subclasses to extend update behaviour. Specify here the desired logic for the scraper to update the candidate_queue.

        Args:
            article: ScrapedElement being processed.
            request_data: Context of the request that discovered it.
        """
        if article not in self.candidate_queue and not article.explored:
            self.candidate_queue.append(article)

    def next_state(self, request_data: RequestData) -> None:
        """
        Update article properties after the request has been executed.

        Args:
            request_data: Context of the completed request.
        """
        raise NotImplementedError

    def generate_request(self) -> tuple[str, RequestData]:
        """
        Returns:
            - URL to fetch
            - RequestData describing the article being analysed and progress state
        """
        next_url = next(self.request_stream)
            
        if self.special_request:
            self.special_request = False
            return next_url, None # We could define fetch_state with something that says that this is a special request, but I want to keep these requests as far away from the scraper behaviour. 

        logger.debug(f"[{len(self.candidate_queue)}] exploring {self.fetch_phase} {self.current_element}")
        request_data = RequestData(self.current_element, self.fetch_phase)
        return next_url, request_data

    def unknown_page(self, articles: list[ScrapedElement]):
        pass

    # Some scrapers may want to overwrite these to access the property of a secondary scraper
    @property
    def current_article(self) -> ScrapedElement:
        return self._current_article

    @current_article.setter
    def current_article(self, value: ScrapedElement):
        self._current_article = value

    @property
    def fetch_phase(self) -> Phase:
        return self._fetch_phase

    @fetch_phase.setter
    def fetch_phase(self, value: Phase):
        self._fetch_phase = value

    # Must be overwritten

    def _fetch_related_papers(self, current_article: ScrapedElement) -> str:
        """
        Main method creating the URL to get the informations about the current article

        Args:
            current_article: ScrapedElement to analyse.

        Yields:
            str: URL to fetch.
        """
        raise NotImplementedError