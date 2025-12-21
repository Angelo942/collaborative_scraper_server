# Scraper

The scraper object handles the logic for deciding which pages to explore, generating URLs for the browser, and updating the server with the parsed data. It is designed to be extended by child classes to handle site-specific scraping logic.

## Core Attributes

The scraper’s state is primarily managed through three attributes:

- `candidate_queue` – A list of articles waiting to be explored.
- `current_article` – The article currently being processed.
- `fetch_phase` – Indicates the current scraping phase (default: CITING, CITED).

Additionally, all discovered articles are stored in:

- known_articles – A dictionary mapping article IDs to article objects for quick lookup and deduplication.

## Core Methods

When writing a child class, these are the main methods you need to focus on:

- `_fetch_related_papers(current_article)`
Generates all URLs required to retrieve information for a given article (e.g., papers citing it or cited by it).

- `_update_impl(article, request_data)`
Defines how newly discovered articles are processed and which ones are added to the candidate queue for further exploration.

- `_pop_next_article()`
Determines the next article to explore from the candidate queue. Can be customized to implement prioritization strategies.

## Generate requests

The `_fetch_related_papers` method is a generator that yields all the URLs required to explore a given article. You can update `fetch_phase` to distinguish between citing and cited papers or implement any phase-specific logic.

Example:

```py
from collaborative_scraper.parse_html.extra.target_site import get_papers_citing, get_papers_cited

def _fetch_related_papers(self, current_article: Article) -> str:
    """
    Main method creating the URL to get the informations about the current article

    Args:
        current_article: Article to analyse.

    Yields:
        str: URL to fetch.
    """
    self.fetch_phase = Phase.CITING
    yield get_papers_citing(current_article)

    self.fetch_phase = Phase.CITED
    yield get_papers_cited(current_article)
```

Notes:

- Update fetch_phase appropriately to allow `_update_impl` to handle discovered articles differently depending on whether they are citing or cited.

## Processing Discovered Articles

Once pages are fetched and parsed, `_update_impl` is called for each discovered article. This is where you decide which articles to enqueue for further exploration.

Example:

```py
def _update_impl(self, article: Article, request_data: RequestData) -> None:
    # Ignore articles that don't come from a request of the scraper
    if request_data is None:
        return
    # Ignore references, only explore the new papers that cite the current article
    if request_data.fetch_state == Phase.CITING:
        self.candidate_queue.append(article)
```

## Selecting the Next Article

The scraper uses candidate_queue to decide which article to explore next. By default, `_pop_next_article` selects the article with the highest priority according to the article’s `__gt__` implementation.

Example (priority-based selection):

```py
def _pop_next_article(self) -> Article | None:
    """
    Select the next article to explore from the candidate queue.

    Articles are prioritized using their __gt__ implementation.

    Returns:
        Article | None: Selected article, or None if the queue is empty.
    """
    if len(self.candidate_queue) != 0:
        next_article = max(self.candidate_queue)
        self.candidate_queue.remove(next_article)
        return next_article
    return None
```

Alternative: LIFO queue (first-in, first-out):

```py
def _pop_next_article(self) -> Article | None:
    """
    Select the next article to explore from the candidate queue.

    Articles are prioritized using their __gt__ implementation.

    Returns:
        Article | None: Selected article, or None if the queue is empty.
    """
    if len(self.candidate_queue) != 0:
        next_article = self.candidate_queue.pop(0)
        return next_article
    return None
```
