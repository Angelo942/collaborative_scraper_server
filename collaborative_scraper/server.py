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

if args.info:
    print(f"database located at: {find_database(target)}")
    exit()

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
        scraper.unknown_page(elements)
    else:
        # Corrupted page -> request again
        if elements is None: return jsonify({"status": "ok", "instructions": [{"type": "reload"}]})

        del current_requests[token]

        for element in elements:
            scraper.update(element, request_data)
        request_data.fetch_phase = scraper.next_state(request_data)

    if can_redirect:
        next_page, request_data = scraper.generate_request(request_data)

        if next_page is None:
            instructions += [
                {
                    "type": "insert_html",
                    "selector": "body",
                    "position": "afterbegin",
                    "html": (
                        "<div id='server-banner' "
                        "style='position:fixed;left:0;right:0;top:0;background:#fffae6;"
                        "padding:8px;border-bottom:1px solid #e6db9a;z-index:99999;'>"
                        "Thank you, but no pages are needed at the moment</div>"
                    )
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
