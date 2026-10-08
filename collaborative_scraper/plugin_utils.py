from collections.abc import Callable

from collaborative_scraper.scrapers.base import BaseScraper
from collaborative_scraper.utils import whitelist_project_name

class Registrar:
    """Handed to a plugin's register(). Collects declarations; commits nothing.

    Keys here are unqualified — the project prefix is applied by Registry.install.

    A plugin only ever calls the setters (``project``, ``parser``, ``scraper``)
    and the registry reads the collected values back off the attributes.

    Nothing here mentions databases: a store is the plugin's own business. The
    core resolves *where* it goes (``cfg["db_file"]``, a file in the project folder) and
    the plugin's factory opens it with whatever class it likes.
    """

    def __init__(self, plugin: str):
        self.plugin = plugin          # entry point name, used in error messages
        self.project_name = None
        self.parsers = {}             # url pattern -> parser
        self.scrapers = {}            # variant -> scraper_factory

    def project(self, name: str) -> None:
        if self.project_name is not None:
            raise ValueError(
                f"project() called twice ({self.project_name!r}, then {name!r})")
        # The name becomes a directory under the user's data dir, so hold it to
        # the whitelist instead of only excluding the separators we parse on.
        if not name or not whitelist_project_name(name):
            raise ValueError(
                f"invalid project name {name!r}: letters, digits and _ only")
        self.project_name = name

    def parser(self, pattern: str, fn) -> None:
        """Parse pages whose url matches ``pattern``: ``"*"``, ``"site.com"`` (and its
        subdomains), ``"www.site.com"`` or ``"www.site.com/page"`` (and the pages below
        it). The most specific match wins; see ``parse_html/parser.py:best_match``."""
        host, _, path = pattern.strip().partition("/")
        pattern = "/".join([host.lower(), *(s for s in path.split("/") if s)])
        if not callable(fn):
            raise TypeError(f"parser for {pattern!r} is not callable: {fn!r}")
        if pattern in self.parsers:
            raise ValueError(f"parser for {pattern!r} declared twice")
        self.parsers[pattern] = fn

    def scraper(self, variant: str, factory: Callable[..., BaseScraper]) -> None:
        self._check_variant(variant)
        if not callable(factory):
            raise TypeError(f"factory for {variant!r} is not callable: {factory!r}")
        if variant in self.scrapers:
            raise ValueError(f"variant {variant!r} declared twice")
        self.scrapers[variant] = factory

    def _check_variant(self, variant: str) -> None:
        if not variant or variant != variant.strip():
            raise ValueError(f"invalid variant name {variant!r}")
        if ":" in variant:
            raise ValueError(
                f"variant {variant!r} must not contain ':' — declare the bare "
                f"variant and the project prefix is added for you, so "
                f"{variant.split(':')[-1]!r} here gives the target "
                f"{self.project_name or '<project>'}:{variant.split(':')[-1]}")

