from collaborative_scraper.databases.utils import find_database
import logging

logger = logging.getLogger(__name__)

# Map each project name to its database class (databases/extra/<project>/...).
# Example:
#   from collaborative_scraper.databases.extra.myproject.my_database import MyDatabase
supported_targets = {
    # "myproject": MyDatabase,
}

def get_database(target: str):
    path = find_database(target)
    DB = supported_targets[target]
    return DB(path)
