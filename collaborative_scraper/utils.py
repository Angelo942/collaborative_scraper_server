from pathlib import Path
from platformdirs import user_data_dir
import logging
import string
from datetime import datetime

from collaborative_scraper.config import project_config
from collaborative_scraper import APP_NAME

logger = logging.getLogger(__name__)

def whitelist_project_name(name: str) -> bool:
    alphabet = string.ascii_letters + string.digits + "_"
    for letter in name:
        if letter not in alphabet:
            return False
    return True

def get_project_dir(project_name: str) -> Path:
    """Everything this project writes (database, snapshots) lives here.

    Overridable per project from the config file::

        [projects.scopus]
        folder = "/mnt/data/scopus"
    """
    folder = project_config(project_name).get("folder")
    if folder:
        project_dir = Path(folder).expanduser()
    else:
        project_dir = Path(user_data_dir(APP_NAME)) / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir

def save_snapshot(payload: dict, SNAPSHOT_DIR: Path) -> None:
    # Save snapshot to disk for inspection
    html = payload.get("html", "")
    meta = payload.get("meta", {})
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    url_safe = meta.get("url", "unknown").replace(":", "_").replace("/", "_")[:80]
    fname = f"{timestamp}_{url_safe}.html"
    path = SNAPSHOT_DIR / fname
    try:
        path.write_text(html)
        logger.debug("[SNAPSHOT] Saved HTML snapshot to %s", path)
        return path
    except Exception as e:
        logger.error("[SNAPSHOT] Error saving HTML snapshot: %s", e)
        raise e
