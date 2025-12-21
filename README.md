# Collaborative Scraper (Server)

This is a backend server for a collaborative web-scraping system.
It allows teams to collect structured data from websites by sending HTML pages to the server using it's [browser extension](https://github.com/Angelo942/collaborative_scraper_extension). The server parses the pages, stores results in a database, and manages which pages should be crawled next.

The system is modular: parsing logic and scraping strategy are fully customizable for different projects and data sources.

---

## Usage overview

0. Install your desired parsers and scrapers.
1. Start the server.
2. Connect the browser extension or client to the server IP.
3. From the client navigate to one of the websites to be parse.

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Angelo942/collaborative_scraper_server.git
cd collaborative_scraper
```

Follow the instructions to configure parsers and scrapers

Finally run the server:

```bash
pip install -r requirements.txt
python3 -m collaborative_scraper.server
```

---

## Key Components

1. Parsers

- Extract structured information from raw HTML pages.
- Each website requires a dedicated parser because HTML structures differ.
- Modular: you can add, replace, or customize parsers per domain.

2. Scrapers

- Decide what extracted data to store and which pages to crawl next.
- Manage crawling strategy and prioritization.
- Modular: you can add or replace scrapers to suit your project workflow.

Since the parsers and scrapers are so specific to your goal here we only include the base structure for the project. You can write your own modules or download pre-made ones.

---

## Parser

Each website has a different HTML structure, so a dedicated parser is required for each supported domain.

### Adding a Parser

Copy your parser module in:

`collaborative_scraper/parse_html/extra/`

If you want to write your own you can find instructions [here](docs/parser.md)

Register the parser in:

`collaborative_scraper/parse_html/parser.py`

with:

```py
# Assuming you installed a parser for target_website_1 and target_website_2
from collaborative_scraper.parse_html.extra.target_website_1 import extract_articles as extract_articles_from_target_website_1
from collaborative_scraper.parse_html.extra.target_website_2 import extract_articles as extract_articles_from_target_website_2

supported_domains = {
    "<www.a_target_website.com>": extract_articles_from_target_website_1,
    "<www.another_target_website.com>": extract_articles_from_target_website_2,
}
```

## Scraper

The scraper defines the crawling strategy. It controls:

- How extracted data is stored
- How new URLs are discovered
- Which pages should be crawled next
- Crawling prioritization logic

### Adding a Scraper

Copy your scraper module in:

`collaborative_scraper/scrapers/extra/`

Select and configure the scraper in:

`collaborative_scraper/scrapers/scraper.py`

Instructions to write your own can be found [here](docs/scraper.md)

by constructing your scraper with the arguments needed and returning it ìn `generate_scraper`

```py
from collaborative_scraper.scrapers.extra.your_scraper import YourScraper

def generate_scraper(db: Database) -> Scraper:
    return = YourScraper(<some_args>, <other_args>, db=db)
```

## Configuration

The server can be configured using a JSON configuration file.

### Default Configuration Location (Linux)

`~/.config/collaborative_scraper/config.json`

### Database Configuration

```json
{"db_path": "/path/to/database.db"}
```

If needed you can specify a path for the database to save the data to. If no configuration file is present, the default value is used: `~/.local/share/collaborative_scraper/data.db`.
