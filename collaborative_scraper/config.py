from functools import lru_cache
from pathlib import Path
from platformdirs import user_config_dir

from collaborative_scraper import APP_NAME

try:                      # 3.11+
    import tomllib
except ModuleNotFoundError:   # 3.10
    import tomli as tomllib

def config_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / "config.toml"

@lru_cache(maxsize=1)
def load_config() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    return tomllib.loads(p.read_text())

def core_settings() -> dict:
    """The ``[core]`` table: settings about the server itself, not about a crawl."""
    return dict(load_config().get("core", {}))

def project_config(project: str) -> dict:
    """The ``[projects.<project>]`` table."""
    return dict(load_config().get("projects", {}).get(project, {}))

def target_config(target: str) -> dict:
    """Merge project-wide settings with variant-specific ones."""
    merged = project_config(target.split(":")[0])
    merged.update(load_config().get("targets", {}).get(target, {}))
    return merged
