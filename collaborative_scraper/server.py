# server.py
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from datetime import datetime
import json
import secrets
import tempfile
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
from collaborative_scraper.parse_html.parser import extract_elements
from collaborative_scraper.utils import save_snapshot, delete_snapshot, whitelist_project_name, get_config_file, get_project_dir
from collaborative_scraper.scrapers.scraper import generate_scraper
from collaborative_scraper.scrapers.scraper import supported_targets
from collaborative_scraper.databases.utils import find_database
import logging
import os
import argparse
from collaborative_scraper.scrapers.base import Phase

log_level = os.getenv("LOG_LEVEL", "WARNING").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.WARNING),
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # allow cross-origin requests from extension

current_requests = {}

parser = argparse.ArgumentParser()
parser.add_argument("project_pos", nargs="?", metavar="project", choices = list(supported_targets.keys()))
parser.add_argument("--project", default=None, choices = list(supported_targets.keys()))
parser.add_argument("--info", action="store_true")
args = parser.parse_args()
if args.project_pos and args.project and args.project_pos != args.project:
    parser.error("project given both positionally and via --project with different values")
args.project = args.project_pos or args.project or "test:passive"

target = args.project
assert len(target.split(":")) == 2
project_name, _ = target.split(":")
assert whitelist_project_name(project_name)
scraper = generate_scraper(target)

if args.info:
    print(f"database for {project_name} located at: {find_database(project_name)}")
    print(f"config file located at {get_config_file()}")
    exit()

@app.route("/ping", methods=["GET"])
def ping():
    # Lightweight health check the client pings on connect to confirm the
    # server is up and working.
    return jsonify({"status": "ok"})

@app.route("/receive", methods=["POST"])
def receive():
    instructions = [] # Commands to send back to the client

    payload = request.get_json(force=True)
    token = payload.get("token")
    can_redirect = payload.get("allow_redirect", True)
    meta = payload.get("meta", {})
    html_page = payload.get("html", "")
    url = meta.get("url", "")
    try:
        elements = extract_elements(html_page, url)
    except Exception as e:
        if log_level == "DEBUG":
            path = get_project_dir(project_name)
            save_snapshot(payload, path)
            logger.critical(f"could not parse elements. Page save {path}")
            raise e
        else:
            logger.warning(f"could not parse elements")
            elements = None

    request_data = current_requests.get(token)
    if request_data is None:
        # Page the client navigated to on its own. If it didn't parse
        # (parser returns None for a page that wasn't fully loaded) there is
        # nothing to record, so skip rather than crash unknown_page.
        if elements is not None:
            # We may want to send also the url in case the scraper wants to decide what to do based on that
            # But the type of the element could already tell that
            # It doesn't say what was the request though, so the full payload could help
            scraper.unknown_page(elements, url)
    else:
        # Corrupted page -> request again
        if elements is None:
            # The page couldn't be parsed. Currently we just ask the client to
            # reload. As an alternative, the standardized banner command can
            # notify the user of the failure (kept unused for now):
            # return jsonify({"status": "ok", "instructions": [
            #     {"type": "banner", "level": "error",
            #      "message": "This page could not be parsed and was skipped."}
            # ]})
            logger.warning("No elements could be extracted. Page likely corrupted")
            return jsonify({"status": "ok", "instructions": [{"type": "reload"}]})

        del current_requests[token]

        for element in elements:
            scraper.update(element, request_data)
        request_data.fetch_phase = scraper.next_state(request_data)

        if request_data.fetch_phase.value == Phase.DONE.value:
            scraper.success(request_data)

    if can_redirect:
        next_page, request_data = scraper.generate_request(request_data)

        if next_page is None:
            # Standardized banner command: the client owns the styling, the
            # server only sends a message and a level ("info" | "error").
            instructions += [
                {
                    "type": "banner",
                    "level": "info",
                    "message": "Thank you, but no more pages are needed at the moment",
                }
            ]
            return jsonify({"status": "ok", "instructions": instructions})

        request_token = secrets.token_hex(8)
        current_requests[request_token] = request_data
        logger.info("[ASSIGNMENT] %s -> %s", request_token, next_page)

        instructions += [
                {"type": "set_token", "token": request_token}
            ]

        instructions += [
            {
                "type": "redirect",
                "url": next_page
            }
        ]
    else:
        logger.debug("User doesn't want to redirect")

    return jsonify({"status": "ok", "instructions": instructions})

if __name__ == "__main__":
    logger.info("[SERVER] Starting server on 127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
