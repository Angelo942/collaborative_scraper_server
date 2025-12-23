from collaborative_scraper.utils import get_config_file
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path

# TODO Use config file
def find_database(project: str) -> Path:
    APP_NAME = __package__.split('.')[0]
    data_dir = Path(user_data_dir(APP_NAME))
    project_dir = data_dir / project
    project_dir.mkdir(exist_ok=True)
    assert project_dir.parent == data_dir
    return project_dir / "data.db"
