from pathlib import Path

def find_database(project_folder: Path, db_file: str) -> Path:
    """Full path of a SQLite file: ``db_file`` inside ``project_folder``.

        [projects.scopus]
        folder = "/mnt/data/scopus"         # project dir: holds all the databases

        [targets."scopus:debug"]
        db_file = "debug.db"                # one variant, its own file
    """
    project_folder = Path(project_folder).expanduser()
    project_folder.mkdir(parents=True, exist_ok=True)
    path = project_folder / db_file
    assert path.parent == project_folder
    return path
