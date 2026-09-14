# server.py
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from datetime import datetime
import json
import secrets
import tempfile
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
from collaborative_scraper.databases.extra.article_database import ArticleDatabase
from collaborative_scraper.parse_html.parser import extract_elements
from collaborative_scraper.utils import save_snapshot, delete_snapshot
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
parser.add_argument("--project", default="scopus:seed_scraper", choices = list(supported_targets.keys()))
parser.add_argument("--info", action="store_true")
args = parser.parse_args()

target = args.project
scraper = generate_scraper(target)
project_name = target.split(":")[0]

if args.info:
    print(f"database located at: {find_database(project_name)}")
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
    elements = extract_elements(payload)

    # Could be merged, but unknown_page gives us some nice control, more than calling multiple update(..., None)
    request_data = current_requests.get(token)
    if request_data is None:
        # Page the client navigated to on its own. If it didn't parse
        # (parser returns None for a page that wasn't fully loaded) there is
        # nothing to record, so skip rather than crash unknown_page.
        if elements is not None:
            scraper.unknown_page(elements)
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
            # instructions += [
            #     {
            #         "type": "banner",
            #         "level": "info",
            #         "message": "Thank you, but no pages are needed at the moment",
            #     }
            # ]
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
