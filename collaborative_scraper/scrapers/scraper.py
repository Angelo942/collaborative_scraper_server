from collaborative_scraper.scrapers.extra.seed_scraper import SeedScraper
from collaborative_scraper.scrapers.extra.scopus_scraper import ScopusScraper as Scraper
from collaborative_scraper.databases.db import get_database

# Import it from the scraper you need to make it available to the ... wait, is it needed ?
# from collaborative_scraper.scrapers.base import RequestData as RequestData

def seed_scraper(db):
    # Handling argument is so much trouble... I almost want to disable the feature.
    return SeedScraper(85018894393, 84879913764, 84879038379, db=db)

def keyword_scraper(db):
    return KeywordScraper([
        "shared control teleoperation",
        "policy blending teleoperation",
        "assisted teleoperation",
        "shared autonomy teleoperation",
        "time delay teleoperation",
        "goal teleoperation",
        "intent teleoperation",
        "intention teleoperation",
        "arbitration teleoperation",
        "shared-control telemanipulation",
        "policy blending telemanipulation",
        "assisted telemanipulation",
        "shared autonomy telemanipulation",
        "goal telemanipulation",
        "intent telemanipulation",
        "intention telemanipulation",
        "arbitration telemanipulation",
        "arbitration shared-control",
        "\"Position predictions\" teleoperation",
        "\"motion prediction\" teleoperation",
        "prediction teleoperation",
        "movement intention prediction",
        "model \"shared control\"",
        "freeform teleoperation",
        "\"free motion\" teleoperation",
        "intention \"shared control\""
        "\"policy adaptation\" teleoperation"
    ], db=db)

def scopus_scraper(db):
    return Scraper(blacklist = lambda element: False, db=db)



supported_targets = {
    "scopus:normal_scraper": scopus_scraper,
    "scopus:keyword_scraper": keyword_scraper,
    "scopus:seed_scraper": seed_scraper,
    "scopus:debug": scopus_scraper,
}

def generate_scraper(target: str) -> Scraper:
    """ User defined function to generate their desired scraper """
    project_name = target.split(":")[0]
    db = get_database(project_name)
    scraper = supported_targets[target](db)
    return scraper

