from collections.abc import Callable
from collaborative_scraper.scrapers.base import BaseScraper, RequestData, Phase
from collaborative_scraper.parse_html.extra.scopus import ScopusArticle as Article, get_papers_citing, get_papers_cited, get_papers_from_keyword
import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)

class Phase(Enum):
    CITING = auto()
    CITED = auto()
    DONE = auto()

def blacklist(article: Article):
    BLACKLIST = [
        "chat",
        "digital",
        "twin",
        "industry",
        "industrial",
        "iot ",
        "internet of things",
        "manufacturing",
        "artificial intelligence",
        " ai ",
        "5.0",
        "4.0",
        "5g",
        "6g",
        "network",
        "metaverse",
        "driving",
        "brain",
        "neuro",
        "face",
        "sustainable",
        "sustainability",
        "city",
        "cities",
        "construction",
        "building",
        # "cement", # have to remove it to not block "reinforcement"
        "power plant", # Power ?
        "blockchain",
        "financ",
        "social",
        "3d print",
        "batter",
        "smart",
        "language",
        "led",
        "quantum",
        "light",
        "photo",
        "metal",
        "carbon",
        "organic",
        "hydro",
        "bio",
        "cardio",
        "laser",
        "sensor",
        "crystal",
        "electr",
        "social",
        "health",
        "palpation",
        "covid",
        "pandemic",
        "road",
        "pedestrian",
        "swarm",
        "aerial",
        "uav",
        "mobile",
        "surgical",
        "surg",
        "vehicle",
        "distributed",
        "lidar",

        "design",
        "wear",
        "soft",
        "future",
        "multiagent",

        "a survey of augmented reality",
        "deep reinforcement learning: a survey",
        "guidelines",
        "european",
        "tutorial",
    ]

    for name in BLACKLIST:
        if name in article.title.lower():
            return True
    return False

class ScopusScraper(BaseScraper):
    def __init__(self, *args, blacklist: Callable[[Article], bool] = blacklist, **kwargs):
        super().__init__(*args, blacklist = blacklist, **kwargs)
        self.known_articles = {article.id : article for article in self.db.get_articles()}
        self.candidate_queue = [article for article in self.known_articles.values() if not article.explored]
        logger.debug("candidate_queue with %d elements", len(self.candidate_queue))
        self.debug_counter = 0

    def _pop_next_article(self) -> Article | None:
        if self.debug_counter >= 2:
            return None

        if len(self.candidate_queue) != 0:
            next_article = max(self.candidate_queue)
            self.candidate_queue.remove(next_article)
            self.candidate_waiting.append(next_article)
            self.debug_counter += 1
        else:
            next_article = None
        return next_article

    def unknown_page(self, articles: list[Article]):
        if articles is not None:
            logger.debug("received %d articles", len(articles))
            for article in articles:
                self.update(article)

    def update(self, article: Article, request_data: RequestData = None) -> None:
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
            if request_data.fetch_phase == Phase.CITING and article.id not in request_data.requested_element.citing: 
                request_data.requested_element.citing.append(article.id)
            elif request_data.fetch_phase == Phase.CITED and article.id not in request_data.requested_element.cited:
                request_data.requested_element.cited.append(article.id)

    def _update_impl(self, article: Article, request_data: RequestData) -> None:
        """Hook for subclasses to extend update behaviour."""
        if article not in self.candidate_queue and not article.explored:
            logger.debug("adding %s to the queue", article)
            self.candidate_queue.append(article)
            
    def next_state(self, request_data: RequestData) -> Phase:
        if request_data.fetch_phase == Phase.CITING:
            if len(request_data.requested_element.citing) >= request_data.requested_element.num_citing:
                return Phase.CITED
            return Phase.CITING
        
        elif request_data.fetch_phase == Phase.CITED:
            old_num_cited = request_data.requested_element.num_cited
            request_data.requested_element.num_cited = len(request_data.requested_element.cited)
            if len(request_data.requested_element.cited) % 200 != 0 or len(request_data.requested_element.cited) == old_num_cited:
                request_data.requested_element.explored = True
                self.db.update_element(request_data.requested_element)
                self.candidate_waiting.remove(request_data.requested_element)
                return Phase.DONE
            return Phase.CITED

    def clear_references(self, request_data: RequestData):
        """
        Util method to remove corrupted citation and reference links.
        """
        logger.warning("clearing: %s", request_data)
        if request_data.fetch_phase == Phase.CITING:
                request_data.requested_element.citing = []
                self.db.update_element(request_data.requested_element)
        if request_data.fetch_phase == Phase.CITED:
                request_data.requested_element.cited = []
                self.db.update_element(request_data.requested_element)

    def _fetch_related_papers(self, request_data: RequestData) -> str:
        if request_data.fetch_phase == Phase.CITING:
            assert len(request_data.requested_element.citing) % 200 == 0, request_data.requested_element
            return get_papers_citing(request_data.requested_element, len(request_data.requested_element.citing))
            
        elif request_data.fetch_phase == Phase.CITED:
            if request_data.requested_element.num_citing % 200 != 0:
                self.clear_references(request_data)
            return get_papers_cited(request_data.requested_element, len(request_data.requested_element.cited))

    def generate_request(self, request_data: RequestData) -> tuple[str, RequestData]:
        logger.debug("%s", request_data)
        if request_data is None or request_data.fetch_phase == Phase.DONE:
            next_element = next(self.request_stream)
            if next_element is None:
                return None, None
            request_data = RequestData(next_element, Phase.CITING)
        if (request_data.fetch_phase == Phase.CITING and len(request_data.requested_element.citing) == min(request_data.requested_element.num_citing, 2000)):
            logger.info("skipping papers citing %s", request_data.requested_element)
            for id in request_data.requested_element.citing:
                self._update_impl(self.known_articles[id], RequestData(request_data.requested_element, request_data.fetch_phase))
            request_data.fetch_phase = Phase.CITED

        if (request_data.fetch_phase == Phase.CITED and len(request_data.requested_element.cited) == request_data.requested_element.num_cited) and (request_data.requested_element.num_cited % 200 != 0 or request_data.requested_element.num_cited == 0): # Skip the ones we know are 0
            logger.info("skipping papers cited by %s", request_data.requested_element)
            for id in request_data.requested_element.cited:
                self._update_impl(self.known_articles[id], RequestData(request_data.requested_element, request_data.fetch_phase))            
            request_data.fetch_phase = Phase.DONE

        if request_data.fetch_phase == Phase.DONE:
            return self.generate_request(request_data) # Could also just call with None

        next_url = self._fetch_related_papers(request_data)
        return next_url, request_data
