from collaborative_webcrawler_server.scrapers.extra.seed_scraper import SeedScraper
from collaborative_webcrawler_server.scrapers.extra.scopus_scraper import ScopusScraper

# scraper = SeedScraper(44949177276, 34547969777, db=db)
# scraper = Scraper(db=db)
# scraper = SeedScraper(85042551265, db=db)

# scraper = KeywordScraper([
    # "shared control teleoperation",
    # "policy blending teleoperation",
    # "assisted teleoperation",
    # "shared autonomy teleoperation",
    # "time delay teleoperation",
    # "goal teleoperation",
    # "intent teleoperation",
    # "intention teleoperation",
    # "arbitration teleoperation",
    # "shared-control telemanipulation",
    # "policy blending telemanipulation",
    # "assisted telemanipulation",
    # "shared autonomy telemanipulation",
    # "goal telemanipulation",
    # "intent telemanipulation",
    # "intention telemanipulation",
    # "arbitration telemanipulation",
    # "arbitration shared-control",
    # "\"Position predictions\" teleoperation",
    # "\"motion prediction\" teleoperation",
    # "prediction teleoperation",
    # "movement intention prediction",
    # "model \"shared control\"",
    # "freeform teleoperation",
    # "\"free motion\" teleoperation",
    # "intention \"shared control\""
    # "\"policy adaptation\" teleoperation"
# ], db=db)

def generate_scraper(db):
    """ User defined function to generate their desired scraper """
    return SeedScraper(85018894393, 84879913764, 84879038379, db=db)
    # return ScopusScraper(db=db)