from collaborative_webcrawler_server.scrapers.base import BaseScraper
from collaborative_webcrawler_server.parse_html.extra.scopus import get_papers_citing, get_papers_cited, get_papers_from_keyword
import logging

logger = logging.getLogger(__name__)

def blacklist(article):
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
    def __init__(self, *args, blacklist = blacklist, **kwargs):
        super().__init__(*args, blacklist = blacklist, **kwargs)

    def _update_impl(self, article, request_data):
        """Hook for subclasses to extend update behaviour."""
        fetch_phase = request_data.get("fetch_phase")
        if fetch_phase == "CITING" or article.num_citing < 100: # Don't follow cited papers that are too popular
            if article not in self.candidate_queue and article.id not in self.explored:
                self.explored.add(article.id)
                self.candidate_queue.append(article)
            
    def _fetch_related_papers(self, current_article):
        self.fetch_phase = "CITING"
        for i in range(current_article.num_citing // 200 + 1):
            yield get_papers_citing(current_article, i*200)
            if self.fetch_phase == "SKIPPING":
                break
            
        # This can not work in parallel
        self.fetch_phase = "CITED"
        self.old_cited_len = -1
        yield get_papers_cited(current_article)
        while len(current_article.cited) % 200 == 0:
            yield get_papers_cited(current_article, offset=len(current_article.cited))
            if len(current_article.cited) == self.old_cited_len:
                print(f"cited exactly {self.old_cited_len} papers")
                break
            self.old_cited_len = len(current_article.cited)

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