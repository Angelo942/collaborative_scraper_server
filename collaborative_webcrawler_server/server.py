# server.py
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from datetime import datetime
import json
import secrets
import tempfile
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
from collaborative_webcrawler_server.db import Database
from collaborative_webcrawler_server.parse_html.parser import extract_articles
from collaborative_webcrawler_server.utils import find_database, save_snapshot, delete_snapshot
from collaborative_webcrawler_server.scrapers.scraper import generate_scraper
import logging
import os

# Get log level from environment, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # allow cross-origin requests from extension

current_requests = {}

db_path = find_database()
db = Database(db_path)
scraper = generate_scraper(db)

@app.route("/receive", methods=["POST"])
def receive():
    instructions = []

    payload = request.get_json(force=True)
    token = payload.get("token")
    can_redirect = payload.get("allow_redirect", True)
    articles = extract_articles(payload)
    
    if token in current_requests: # if token is None should still return False
        request_data = current_requests[token] # Keep old page in case page is corrupted
    
        if articles is None: # Corrupted page -> request again
            return jsonify({"status": "ok", "instructions": [{"type": "reload"}]})

        del current_requests[token]

        for article in articles:
            scraper.update(article, request_data)
        scraper.success(request_data)
    else:
        if articles is not None:
            for article in articles:
                scraper.update(article)
                db.update_page(article)

    if can_redirect:
        next_page, request_data = scraper.next_target() # Will update the state and current article 
        # TODO handle job done
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
        print(f"[ASSIGNMENT] {request_token} -> {next_page}")

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

    # Not implemented yet
    # if scraper.save_zotero:
    #     instruction += {
    #         "type": "zotero_save"
    #     }

    return jsonify({"status": "ok", "instructions": instructions})

if __name__ == "__main__":
    print("[SERVER] Starting server on 127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)