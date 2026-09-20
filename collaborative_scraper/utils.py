from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
import os
import logging
import string
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def whitelist_project_name(name: str) -> bool:
    alphabet = string.ascii_letters + string.digits + "_"
    for letter in name:
        if letter not in alphabet:
            return False
    return True

def get_config_file() -> Path:
    APP_NAME = __package__.split('.')[0]
    config_file = Path(user_config_dir(APP_NAME)) / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    if not config_file.exists():
        config_file.write_text("{}")
    return config_file

def get_project_dir(project_name: str) -> Path:
    config_file = get_config_file()
    config = json.loads(config_file.read_text())
    project_data = config.get(project_name)
    if project_data is not None and "folder" in project_data:
        project_dir = Path(project_data["folder"])
    else:
        APP_NAME = __package__.split('.')[0]
        data_dir = Path(user_data_dir(APP_NAME))
        project_dir = data_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir

def guarded_int(value: str, description: str = "") -> int:
    """ int() that logs a critical message identifying the offending value before re-raising. """
    try:
        return int(value)
    except ValueError as e:
        logger.critical("can't convert %r to int%s", value, f" ({description})" if description else "")
        raise e

def safe_int(value: str) -> int:
    try:
        return formatted_int(value)
    except ValueError:
        return 0

def formatted_int(value: str) -> int:
    return int(value.replace(",", "").replace(".", "").replace("_", ""))

def formatted_float(value: str) -> int:
    return float(value.replace(".", "").replace(",", "."))

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

def delete_snapshot(path: Path, SNAPSHOT_DIR: Path) -> None:
    try:
        if  path.parent == SNAPSHOT_DIR:
            os.remove(path)
            # logger.debug("[CLEANUP] Deleted snapshot %s", abs_path)
        else:
            logger.warning("[CLEANUP] Skipped deletion (outside %s): %s", SNAPSHOT_DIR, abs_path)
    except Exception as e:
        logger.error("[CLEANUP] Could not delete %s: %s", path, e)