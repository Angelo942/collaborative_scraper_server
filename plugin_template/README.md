# collaborative_scraper plugin template

The smallest working plugin: it accepts a page from any website and prints it.
Copy this folder to start a new plugin, then rename it.

## Try it

```bash
pip install -e plugin_template
python3 -m collaborative_scraper.server template:debug
```

Browse with the extension. Each page the server receives is printed to its console.

## Making it your own

1. Rename the package folder, `name` in `pyproject.toml`, the entry point name and its target `<module>:register`.
2. In `register()`:
   - `reg.project("<name>")`: the project name. It becomes the target prefix and the project folder.
   - `reg.parser("<pattern>", fn)`: which urls this parser handles. A pattern can be `"site.com"` (that host and all its subdomains), `"www.site.com"`, `"www.site.com/page"` (that path and every page below it) or `"*"` (any url). When several patterns match, the most specific one wins, even across plugins.
   - `reg.scraper("<variant>", factory)`: one call per crawl mode. This creates the target `<project>:<variant>`.
3. `parser.py`: `extract_elements(html_page, url, request_data)` gets the full url of the page and the server's request it answers (`None` for a page the client navigated to on its own). Subclass `ScrapedElement` for each kind of item and return them wrapped in a `Result`. Return `None` when the page is not fully loaded.
4. `scraper.py`: a passive scraper overrides only `unknown_page`. An active scraper also overrides `update`, `next_state`, `generate_request` and optionally `success`. See `BaseScraper` for details.
5. For storage, subclass `ScraperDatabase`, implement `_init_db`, and open it in the factory with `cfg["db_file"]`.

Import only from `collaborative_scraper.api`.

Settings for one target go in the core's `config.toml` and reach the factory as `cfg`:

```toml
[targets."template:debug"]
db_file = "template.db"
```

To debug without `pip install`, list the plugin folder in the `[core]` table of `config.toml`:

```toml
[core]
plugins = ["/path/to/plugin_template"]
```

The server puts that folder on the import path and loads the entry point from its `pyproject.toml`. Remove it from the list once the plugin is installed: it would otherwise be loaded twice.
