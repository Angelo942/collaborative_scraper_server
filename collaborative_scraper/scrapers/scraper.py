from collaborative_scraper.scrapers.base import BaseScraper
from collaborative_scraper.databases.db import get_database

# Register your project's scrapers here.
#   1. Import a scraper from your installed plugin (scrapers/extra/<project>/...).
#   2. Wrap it in a factory that takes `db` and returns an instance.
#   3. Register that factory under a "<project>:<variant>" key.
#
# Example:
#   from collaborative_scraper.scrapers.extra.myproject.my_scraper import MyScraper
#   def my_scraper(db):
#       return MyScraper(db=db)

supported_targets = {
    # "myproject:default": my_scraper,
}

def generate_scraper(target: str) -> BaseScraper:
    """ Build the scraper registered for the given "<project>:<variant>" target. """
    project_name = target.split(":")[0]
    db = get_database(project_name)
    scraper = supported_targets[target](db)
    return scraper
