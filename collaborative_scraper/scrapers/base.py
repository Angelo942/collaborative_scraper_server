from enum import Enum, auto
from collections.abc import Callable
from collaborative_scraper.parse_html.base import ScrapedElement
import logging

logger = logging.getLogger(__name__)

class Phase(Enum):
    STARTED = auto()
    DONE = auto()

class RequestData:
    def __init__(self, requested_element: ScrapedElement, fetch_phase: Phase):
        self.requested_element = requested_element
        self.fetch_phase = fetch_phase

    def __repr__(self):
        return f"{self.requested_element=}, {self.fetch_phase}"

# To work in a distributed manner it must become partially stateless...
class BaseScraper:
    def __init__(self, db, blacklist: Callable[[ScrapedElement], bool] = lambda element: False):
        self.db = db
        self.blacklist = blacklist # Allow to define rules to prevent exploring certain results
        self._fetch_phase = None
        self.request_stream = self._request_generator()
        self.candidate_queue = []
        self.candidate_waiting = [] # Put here element that are being processed
        self.special_request = False

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
                next_article = self.known_articles[paper_id]
                logger.info("[SPECIAL REQUEST] %s", next_article)
            else:
                self.special_request = False
                next_article = self._pop_next_article() # Who should be responsible to add the elements to candidate_waiting ? Maybe _request_generator instead of _pop_next_article
                if next_article is None:
                    yield None
                    continue
                if self.blacklist(next_article):
                    logger.info("[blacklisted] %s", next_article)
                    continue
            yield next_article

    def update(self, article: ScrapedElement, request_data: RequestData = None) -> None:
        """
        Update internal state given a discovered article.

        Args:
            article: Parsed article to integrate.
            request_data (optional):
                Context describing which request triggered this update.
        """
        raise NotImplementedError

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
            self.candidate_waiting.append(next_article)
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
        request_data.fetch_phase = Phase.DONE

        if request_data.fetch_phase == Phase.DONE:
            self.candidate_waiting.remove(request_data.requested_element)

        raise NotImplementedError

    def generate_request(self, request_data: RequestData = None) -> tuple[str, RequestData]:
        """
        Returns:
            - URL to fetch
            - RequestData describing the article being analysed and progress state
        """
        raise NotImplementedError

    def unknown_page(self, articles: list[ScrapedElement]):
        pass

    # Must be overwritten

    def _fetch_related_papers(self, request_data: RequestData) -> str:
        """
        Main method creating the URL to get the informations about the current article

        Args:
            current_article: ScrapedElement to analyse.

        Yields:
            str: URL to fetch.
        """
        raise NotImplementedError