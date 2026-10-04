# Collaborative Scraper (Server)

This is a backend server for a collaborative web-scraping system.
It allows teams to collect structured data from websites by sending HTML pages to the server using its [browser extension](https://github.com/Angelo942/collaborative_scraper_extension). The server parses the pages, stores results in a database, and manages which pages should be crawled next.

The server itself is generic: everything specific to a website or project (parsers, crawling strategy, database schema) lives in **plugins**, separate pip-installable packages the server discovers at startup.

---

## Usage overview

0. Install the server and the plugin(s) for the sites you want to crawl.
1. Start the server on one of the targets the plugins provide.
2. Connect the browser extension to the server IP.
3. From the client navigate to one of the websites to be parsed.
4. Run the extension to start sending pages to the server.

---

## Installation

```bash
git clone https://github.com/Angelo942/collaborative_scraper_server.git
cd collaborative_scraper_server
pip install -e .
```

Then install one or more plugins (each is its own package):

```bash
pip install -e /path/to/plugin-scopus
```

## Running

A target is `project:variant`, e.g. `scopus:seed_scraper`. There is no default:

```bash
collaborative_scraper --list-targets
collaborative_scraper scopus:seed_scraper
```

`python3 -m collaborative_scraper.server` works the same way.

| option | |
| --- | --- |
| `--list-targets` | every target and the plugin providing it |
| `--list-plugins` | installed plugins and their versions |
| `--info` | project folder, database file and config file path for a target |
| `--host` / `--port` | default `127.0.0.1` / `5000` |
| `--debug` | Flask debug mode |

A plugin that fails to load is logged and skipped, not fatal. If a target you expect is missing from `--list-targets`, read the logged traceback (or run with `LOG_LEVEL=DEBUG`).

---

## Key Components

1. **Parsers** extract structured information from raw HTML pages. Each website needs a dedicated parser, registered per host.
2. **Scrapers** decide what extracted data to store and which pages to crawl next. A project can offer several variants (e.g. a passive one that only records what the user visits, and an active one that drives the client).
3. **Databases** persist the results. Each plugin brings its own SQLite schema; the server only decides where the file lives.

---

## Writing a plugin

A plugin is a normal Python package that declares an entry point in the `collaborative_scraper.plugins` group, pointing at a `register(reg)` function:

```toml
# the plugin's pyproject.toml
[project.entry-points."collaborative_scraper.plugins"]
mysite = "collaborative_scraper_mysite:register"
```

```python
# collaborative_scraper_mysite/__init__.py
from collaborative_scraper.api import BaseScraper, ScraperDatabase, ScrapedElement

def register(reg):
    reg.project("mysite")                              # exactly once: owns the "mysite:" namespace
    reg.parser("www.mysite.com", extract_elements)     # host -> parser
    reg.scraper("passive", _passive)                   # bare variant -> target "mysite:passive"

def _passive(cfg):
    # cfg is the target's config table; cfg["db_file"] is the resolved database path
    return MyPassiveScraper(MyDatabase(cfg["db_file"]))
```

Import only from `collaborative_scraper.api` — it re-exports everything a plugin needs (`ScrapedElement`, `Result`, `BaseScraper`, `RequestData`, `GETRequest`, `POSTRequest`, `FETCHRequest`, `Phase`, `DONE`, `is_done`, `ScraperDatabase`, `Registrar`).

- **Parser**: `extract_elements(html_page, path, get_parameters, post_parameters) -> Result | None`. Wrap the parsed elements in a `Result` (with optional `metadata`), or return `None` when the page wasn't fully loaded. See [docs/parser.md](docs/parser.md).
- **Scraper**: a subclass of `BaseScraper`, built by the factory passed to `reg.scraper`. See [docs/scraper.md](docs/scraper.md).
- **Database**: a subclass of `ScraperDatabase`. It is not registered; your factory opens it.

### Prototyping without packaging

Load an importable module's `register()` without an entry point:

```bash
COLLABORATIVE_SCRAPER_PLUGINS=my_module collaborative_scraper mysite:passive
```

or list it in the config file (below) under `[core] plugins = ["my_module"]`.

---

## Configuration

One TOML file, `config.toml`, in the user config directory (`~/.config/collaborative_scraper/config.toml` on Linux; `--info` prints the exact path). Every table is optional.

```toml
[core]
plugins = ["my_module"]              # extra unpackaged plugins

[projects.scopus]
folder = "/mnt/data/scopus"          # project folder: database + snapshots

[targets."scopus:debug"]
db_file = "debug.db"                 # a file name inside the project folder
seeds = ["..."]                      # any other key is passed to the plugin's factory
```

- The project folder defaults to `~/.local/share/collaborative_scraper/<project>` on Linux.
- `db_file` defaults to `<project>.db` and always lives inside the project folder; to move a database, move the folder.
- A target's settings are its project table merged with its `[targets."project:variant"]` table.
