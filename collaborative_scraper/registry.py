import importlib
import importlib.metadata as md
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

from collaborative_scraper.plugin_utils import Registrar

logger = logging.getLogger(__name__)
GROUP = "collaborative_scraper.plugins"

class Registry:
    """The live tables the server reads. Written only through install()."""

    def __init__(self):
        self.projects = {}     # "imdb"                 -> plugin name
        self.parsers = {}      # "www.imdb.com"         -> callable(html, url, request_data)
        self.scrapers = {}     # "imdb:passive_scraper" -> callable(cfg)
        self.plugins = {}      # plugin name            -> version
        self._origin = {}      # (kind, key)            -> plugin name

    def install(self, reg: Registrar, version: str = "unknown") -> None:
        """Validate a plugin's declarations in full, then commit them as a unit.

        Nothing in this registry is touched until every check has passed, so a
        plugin that raises here leaves no half-registered project behind.
        """
        project = reg.project_name
        if project is None:
            raise ValueError(f"plugin {reg.plugin!r} never called project()")

        # ---- validate everything before touching the live tables ----
        self._check_free("project", project, reg.plugin,
                         lambda o: f"claims project {project!r}, already provided by {o!r}")
        for host in reg.parsers:
            self._check_free("parser", host, reg.plugin,
                             lambda o, h=host: f"claims parser for {h!r}, already provided by {o!r}")
        for variant in reg.scrapers:
            target = f"{project}:{variant}"
            self._check_free("target", target, reg.plugin,
                             lambda o, t=target: f"claims target {t!r}, already provided by {o!r}")

        # ---- commit: this is where short names become full keys ----
        self.projects[project] = reg.plugin
        self._origin[("project", project)] = reg.plugin

        for host, fn in reg.parsers.items():
            self.parsers[host] = fn
            self._origin[("parser", host)] = reg.plugin

        for variant, factory in reg.scrapers.items():
            target = f"{project}:{variant}"
            self.scrapers[target] = factory
            self._origin[("target", target)] = reg.plugin

        self.plugins[reg.plugin] = version

    def _check_free(self, kind: str, key: str, plugin: str, message) -> None:
        owner = self._origin.get((kind, key))
        if owner is not None:
            raise RuntimeError(f"plugin {plugin!r} " + message(owner))

    def owner(self, target: str) -> str | None:
        """Which plugin provides this target."""
        return self._origin.get(("target", target))

    def targets_of(self, project: str) -> list[str]:
        return sorted(t for t in self.scrapers if t.split(":")[0] == project)

# Kept from the pre-registry wiring: the bundled demos were meant to be
# installed like a plugin but without an install step. The modules it imports
# no longer exist on disk (parse_html/demo, scrapers/demo, databases/demo are
# empty), so it stays commented out until the demo plugin is restored.
# def _register_builtins(registry):
#     """Demos bundled with the core. Not plugins: no install step, always present."""
#     from collaborative_scraper.parse_html.demo import imdb_parser, duckduckgo_demo
#     from collaborative_scraper.scrapers.demo.imdb.demo_passive_scraper import PassiveIMDbScraper
#     from collaborative_scraper.scrapers.demo.duckduckgo.demo_passive_scraper import PassiveScraper
#     from collaborative_scraper.scrapers.demo.duckduckgo.demo_active_scraper import ActiveScraper
#
#     reg = Registrar("builtin")
#     reg.project("test")
#     reg.parser("duckduckgo.com", duckduckgo_demo.extract_elements)
#     reg.parser("www.duckduckgo.com", duckduckgo_demo.extract_elements)
#     reg.parser("www.imdb.com", imdb_parser.extract_elements)
#     reg.scraper("passive",      lambda cfg: PassiveScraper(DemoDatabase(cfg["db_file"])))
#     reg.scraper("active",       lambda cfg: ActiveScraper(DemoDatabase(cfg["db_file"])))
#     reg.scraper("imdb_passive", lambda cfg: PassiveIMDbScraper(DemoDatabase(cfg["db_file"])))
#     registry.install(reg, "builtin")


def _build_registry() -> Registry:
    # Published before loading anything: importing a plugin runs its module
    # body, and a plugin that reaches back into get_registry() would otherwise
    # re-enter this function forever.
    _registry = Registry()
    # _register_builtins(_registry)
    for ep in md.entry_points(group=GROUP):
        _load(_registry, ep.name, ep.load, _plugin_version(ep))
    for entry in _extra_plugins():
        if _is_path(entry):
            for name, resolve, version in _folder_plugins(entry):
                _load(_registry, name, resolve, version)
        else:
            _load(_registry, entry, lambda m=entry: _module_register(m), "local")
    return _registry

@lru_cache(maxsize=1)
def get_registry() -> Registry:
    return _build_registry()

def _load(registry: Registry, name: str, resolve, version: str = "unknown") -> None:
    """Import, run register(), install. Any failure skips this plugin only."""
    registrar = Registrar(name)
    try:
        resolve()(registrar)
        registry.install(registrar, version)
    except Exception:
        logger.exception("plugin %r failed to load; skipping", name)

def _plugin_version(ep) -> str:
    """The version of the distribution the entry point came from."""
    try:
        return ep.dist.version
    except Exception:
        pass
    try:
        return md.version(ep.module.split(".")[0])
    except Exception:
        return "unknown"

def _module_register(module: str):
    """The register() of an importable module, for unpackaged plugins."""
    mod = importlib.import_module(module)
    try:
        return mod.register
    except AttributeError:
        raise AttributeError(f"module {module!r} defines no register(reg)") from None

def _is_path(entry: str) -> bool:
    """A plugin folder rather than a module name: has a separator or starts with ~ or ."""
    return "/" in entry or os.sep in entry or entry.startswith(("~", "."))

def _folder_plugins(entry: str) -> list[tuple]:
    """(name, resolve, version) for each plugin in a folder named by path.

    The folder is a plugin's project root: it goes on ``sys.path`` and the
    ``collaborative_scraper.plugins`` entry points of its ``pyproject.toml`` are
    loaded as if the plugin were installed. A folder without one is taken as a
    bare package: its parent goes on ``sys.path`` and it is imported by name.
    A problem with the folder itself is logged and the entry skipped.
    """
    from collaborative_scraper.config import tomllib

    folder = Path(entry).expanduser().resolve()
    pyproject = folder / "pyproject.toml"
    try:
        if pyproject.is_file():
            project = tomllib.loads(pyproject.read_text()).get("project", {})
            declared = project.get("entry-points", {}).get(GROUP, {})
            if not declared:
                raise ValueError(f"{pyproject} declares no [project.entry-points.\"{GROUP}\"]")
            _add_to_path(folder)
            version = project.get("version", "local")
            return [(name, md.EntryPoint(name, value, GROUP).load, version)
                    for name, value in declared.items()]
        if (folder / "__init__.py").is_file():
            _add_to_path(folder.parent)
            return [(folder.name, lambda m=folder.name: _module_register(m), "local")]
        raise FileNotFoundError(f"{folder} has neither a pyproject.toml nor an __init__.py")
    except Exception:
        logger.exception("plugin folder %r could not be read; skipping", entry)
        return []

def _add_to_path(folder: Path) -> None:
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

def _extra_plugins() -> list[str]:
    """Plugins that are not installed, for prototyping and debugging.

    From ``COLLABORATIVE_SCRAPER_PLUGINS`` (comma separated) and from ``plugins``
    in the ``[core]`` table of config.toml. Each entry is either a plugin folder
    (a path; see ``_folder_plugins``) or an importable module name. Listing the
    same entry twice is harmless; listing a plugin that is *also* installed as
    an entry point is not, and install() rejects the second one by project.
    """
    from collaborative_scraper.config import core_settings

    env = os.getenv("COLLABORATIVE_SCRAPER_PLUGINS", "")
    modules = [m.strip() for m in env.split(",")]
    try:
        modules += [str(m).strip() for m in core_settings().get("plugins", [])]
    except Exception:
        logger.exception("could not read [core] plugins from the config file")

    seen, out = set(), []
    for module in modules:
        if module and module not in seen:
            seen.add(module)
            out.append(module)
    return out
