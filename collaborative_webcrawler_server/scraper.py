from collaborative_webcrawler_server.parse_html.scopus import get_papers_citing, get_papers_cited, get_papers_from_keyword

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

class Scraper:
    def __init__(self, db):
        self.db = db
        self.known_articles = {article.id : article for article in self.db.get_articles()}
        self.generator = self.target_generator()
        self._current_article = None # Start with a manual page
        self.new_articles = []
        self.size_layer = len(self.new_articles)
        self._state = None
        self.passed = False
        self.explored = set()
        self.special_request = False
        self.save_zotero = False

        self.current_layer = [] # Just there for the logs...


    def find_next_article(self):
        self.current_article = max(self.new_articles)
        self.new_articles.remove(self.current_article)
        self.size_layer = len(self.new_articles)

    def target_generator(self):
        while True:
            paper_id = self.db.pop_next_fetch_request()
            if paper_id is not None:
                self.special_request = True
                self.current_article = self.known_articles[paper_id]
                print(f"[SPECIAL REQUEST] {self.current_article}")
            else:
                self.special_request = False
                self.find_next_article()
                if blacklist(self.current_article):
                    print(f"[blacklisted] {self.current_article}")
                    continue
            yield from self.fetch_scopus_papers()
            
    def fetch_scopus_papers(self):
        self.state = "CITING"
        for i in range(self.current_article.num_citing // 200 + 1):
            yield get_papers_citing(self.current_article, i*200)
            if self.state == "SKIPPING":
                break
            
        self.state = "CITED"
        self.old_cited_len = -1
        yield get_papers_cited(self.current_article)
        while len(self.current_article.cited) % 200 == 0:
            yield get_papers_cited(self.current_article, offset=len(self.current_article.cited))
            if len(self.current_article.cited) == self.old_cited_len:
                print(f"cited exactly {self.old_cited_len} papers")
                break
            self.old_cited_len = len(self.current_article.cited)

    def update(self, article):
        if self.special_request:
            return
        if article.id not in self.known_articles:
            self.db.save_page(article)
            self.known_articles[article.id] = article
        else:
            article = self.known_articles[article.id]

        self._update_impl(article)

    def _update_impl(self, article):
        """Hook for subclasses to extend update behavior."""
        if self.state == "CITING" or article.num_citing < 100:
            if article not in self.new_articles and article.id not in self.explored:
                self.new_articles.append(article)
                self.explored.add(article.id)
    
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

    @property
    def next_target(self):
        while True:
            next_link = next(self.generator)
            if (self.state == "CITING" and len(self.current_article.citing) == min(self.current_article.num_citing, 2000)): # There is a limit to 2000 papers on scopus
                print(f"skipping papers citing {self.current_article}")
                for id in self.current_article.citing:
                    self.update(self.known_articles[id]) # Careful to not change the state before calling update
                self.state = "SKIPPING"
            elif (self.state == "CITED" and len(self.current_article.cited) == self.current_article.num_cited) and (self.current_article.num_cited % 200 != 0 or self.current_article.num_cited == 0): # Skip the ones we know are 0
                print(f"skipping papers cited by {self.current_article}")
                for id in self.current_article.cited:
                    self.update(self.known_articles[id])
            else:
                break

        print(f"[{len(self.current_layer)}/{self.size_layer}] exploring {self.state} {self.current_article}")

        return next_link

    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, value):
        self._state = value

    @property
    def current_article(self):
        return self._current_article
    
    @current_article.setter
    def current_article(self, value):
        self._current_article = value

class PopularScraper(Scraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_articles = [self.known_articles[id] for id in self.db.get_unexplored()]
        size_layer = len(self.new_articles)

    def find_next_article(self):
        self.current_article = max(self.new_articles)
        self.new_articles.remove(self.current_article)
        self.size_layer = len(self.current_layer)
        
    def _update_impl(self, article):
        if article not in self.new_articles and article.id not in self.explored:
            self.new_articles.append(article)
            self.explored.add(article.id)

class SeedScraper(Scraper):
    def __init__(self, *seeds, **kwargs):
        super().__init__(**kwargs)
        self.current_layer = [self.known_articles[seed] for seed in seeds]
        self.size_layer = len(self.current_layer)
        self.explored = {id for id in seeds}
        self.next_layer = set()

    def find_next_article(self):
        if len(self.current_layer) == 0:# or max(self.current_layer).num_citing < 1:
            self.current_layer = self.next_layer
            self.size_layer = len(self.current_layer)
            self.next_layer = set()

        self.current_article = max(self.current_layer)
        self.current_layer.remove(self.current_article)
        # self.current_article = self.current_layer.pop() # Take a random element to go faster
                    
    def _update_impl(self, article):
        # Don't save cited papers. The idea is that the papers we have are already the most important ones and you don't care about what they cite if it's not cited anymore anyway.
        if self.state == "CITING":
            if article not in self.next_layer and article.id not in self.explored and article.num_citing >= 5:
                self.next_layer.add(article)
                self.explored.add(article.id)

class KeywordScraper(Scraper):
    def __init__(self, keywords, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords
    
    def find_next_article(self):
        for article in self.new_articles:
            for keyword in self.keywords:
                if keyword in article.title.lower():
                    break
        else:
            article = max(self.new_articles)
        self.current_article = article
        self.new_articles.remove(self.current_article)

    def _update_impl(self, article):
        # Don't save cited papers. The idea is that those are already the most important ones and you don't care about what they cite if it's not cited anymore anyway.
        if self.state != "CITED":
            if article not in self.new_articles and article.id not in self.explored:
                self.new_articles.append(article)
                self.explored.add(article.id)

class KeywordScraper(Scraper):
    def __init__(self, keywords, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords
        self.current_keyword = None
        self.discovered = [] # Could use explored
        self.done = False
        self.second_scraper = None
        self.known_queries = self.db.get_queries()

    def target_generator(self):
        yield from self.fetch_scopus_papers()
    
    def fetch_scopus_papers(self):
        for keyword in self.keywords:
            if keyword in self.known_queries:
                print(f"skipping query: {keyword}")
                for id in self.db.get_query_results(keyword):
                    self.discovered.append(self.known_articles[id])
                continue
            self.known_queries.append(keyword)
            self.current_keyword = []
            self.old_counter = 0
            while len(self.current_keyword) % 200 == 0:
                yield get_papers_from_keyword(keyword, len(self.current_keyword))
                if len(self.current_keyword) == self.old_counter:
                    print(f"found exactly {self.old_counter} papers")
                    break
                self.old_counter = len(self.current_keyword)
            self.db.save_query(keyword, self.current_keyword, "scopus")
        self.done = True

    def _update_impl(self, article):
        if self.current_keyword is None:
            return
        if article not in self.discovered:
            self.discovered.append(article)
        self.current_keyword.append(article.id)

    @property
    def next_target(self):
        for target in self.generator:
            return target
        if self.done:
            print("WE ARE DONE LOOKING FOR KEYWORDS")
            self.second_scraper = SeedScraper(*[article.id for article in self.discovered])
            self.second_scraper.known_articles = self.known_articles # Keep updating both at the same time
            self.done = False
        return self.second_scraper.next_target

    @property
    def state(self):
        if self.second_scraper is None:
            return None
        else:
            return self.second_scraper.state

    @property
    def current_article(self):
        if self.second_scraper is None:
            return None
        else:
            return self.second_scraper.current_article