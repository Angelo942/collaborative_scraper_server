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
    if "db_dir" in config:
        data_dir = Path(config["db_dir"])
    else:
        data_dir = Path(user_data_dir(APP_NAME))
        data_dir.mkdir(exist_ok=True)
        config["db_dir"] = str(data_dir)
        config_file.write_text(json.dumps(config))
    if "db_name" in config:
        db_name = config["db_name"]
    else:
        db_name = "default.db"
        config["db_name"] = db_name
        config_file.write_text(json.dumps(config))
    return data_dir / db_name

def save_snapshot(payload, SNAPSHOT_DIR) -> None:
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

def delete_snapshot(path, SNAPSHOT_DIR) -> None:
    try:
        if  path.parent == SNAPSHOT_DIR:
            os.remove(path)
            # print(f"[CLEANUP] Deleted snapshot {abs_path}")
        else:
            print(f"[CLEANUP] Skipped deletion (outside {SNAPSHOT_DIR}): {abs_path}")
    except Exception as e:
        print(f"[CLEANUP] Could not delete {path}: {e}")