from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
import os
import json

def find_database() -> str:
    APP_NAME = __package__.split('.')[0]
    config_file = Path(user_config_dir(APP_NAME)) / "config.json"
    config_file.parent.mkdir(exist_ok=True)
    if config_file.exists() and (data := config_file.read_text()):
        config = json.loads(data)
    else:
        config = {}
    if "db_path" in config:
        db_path = Path(config["db_path"])
    else:
        data_dir = Path(user_data_dir(APP_NAME))
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "data.db"
        config["db_path"] = str(db_path)
        config_file.write_text(json.dumps(config))
    return db_path

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
        # print(f"[SNAPSHOT] Saved HTML snapshot to {path}")
        return path
    except Exception as e:
        print(f"[SNAPSHOT] Error saving HTML snapshot: {e}")
        raise e

def delete_snapshot(path: Path, SNAPSHOT_DIR: Path) -> None:
    try:
        if  path.parent == SNAPSHOT_DIR:
            os.remove(path)
            # print(f"[CLEANUP] Deleted snapshot {abs_path}")
        else:
            print(f"[CLEANUP] Skipped deletion (outside {SNAPSHOT_DIR}): {abs_path}")
    except Exception as e:
        print(f"[CLEANUP] Could not delete {path}: {e}")