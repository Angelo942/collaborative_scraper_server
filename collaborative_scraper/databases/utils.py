from collaborative_scraper.utils import get_config_file, get_project_dir
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path

# TODO Use config file to allow user to select another folder
def find_database(project_name: str) -> Path:
    return get_project_dir(project_name)
