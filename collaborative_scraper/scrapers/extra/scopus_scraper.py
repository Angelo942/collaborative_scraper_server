from collections.abc import Callable
from collaborative_scraper.scrapers.base import BaseScraper, RequestData, Phase
from collaborative_scraper.parse_html.extra.scopus import ScopusArticle as Article, get_papers_citing, get_papers_cited, get_papers_from_keyword
import logging

logger = logging.getLogger(__name__)

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

    def _update_impl(self, article: Article, request_data: RequestData) -> None:
        """Hook for subclasses to extend update behaviour."""
        if request_data is None:
            return
        if request_data.fetch_phase == Phase.CITING or article.num_citing < 100: # Don't follow cited papers that are too popular
            if article not in self.candidate_queue and article.id not in self.explored:
                self.explored.add(article.id)
                self.candidate_queue.append(article)
            
    def _fetch_related_papers(self, current_article: Article) -> str:
        self.fetch_phase = Phase.CITING
        for i in range(current_article.num_citing // 200 + 1):
            yield get_papers_citing(current_article, i*200)
            if self.fetch_phase == Phase.SKIPPING:
                break
            
        # This can not work in parallel
        self.fetch_phase = Phase.CITED
        self.old_cited_len = -1
        yield get_papers_cited(current_article)
        while len(current_article.cited) % 200 == 0:
            yield get_papers_cited(current_article, offset=len(current_article.cited))
            if len(current_article.cited) == self.old_cited_len:
                logger.debug(f"cited exactly {self.old_cited_len} papers")
                break
            self.old_cited_len = len(current_article.cited)

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