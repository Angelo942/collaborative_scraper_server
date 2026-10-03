from collaborative_scraper.databases.utils import find_database
from collaborative_scraper.registry import get_registry
from collaborative_scraper.scrapers.base import BaseScraper
from collaborative_scraper.utils import get_project_dir
from collaborative_scraper.config import target_config

def supported_targets() -> list[str]:
    return sorted(get_registry().scrapers)

def scraper_config(target: str) -> dict:
    """The target's config table with ``db_file`` resolved to a full path.

    The config names the database by bare file name (default ``<project>.db``);
    it is placed in the project folder.
    """
    project = target.split(":")[0]
    cfg = target_config(target)          # a fresh dict, safe to add to
    cfg["db_file"] = find_database(get_project_dir(project),
                                   cfg.get("db_file", f"{project}.db"))
    return cfg

# We may want to have a default request_data to allow tracking passive clients
def generate_scraper(target: str) -> BaseScraper:
    """Build the scraper for one target.

    the factory opens whatever class it likes there. the plugin's own - ``seeds``,
    ``keywords``, ``blacklist``, whatever the variant reads
    """
    registry = get_registry()
    try:
        factory = registry.scrapers[target]
    except KeyError:
        raise SystemExit(
            f"unknown target {target!r}. Available: {supported_targets()}")
    return factory(scraper_config(target))
