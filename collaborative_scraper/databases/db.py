from collaborative_scraper.databases.extra.article_database import ArticleDatabase
from collaborative_scraper.databases.utils import find_database
import logging

logger = logging.getLogger(__name__)

supported_targets = {
    "scopus": ArticleDatabase,
}

def get_database(target: str):
    path = find_database(target)
    DB = supported_targets[target]
    return DB(path)