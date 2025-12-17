# server.py
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from datetime import datetime
import os
import json
import secrets
import tempfile
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
from collaborative_webcrawler_server.parse_html.scopus import extract_articles as extract_articles_from_scopus
from collaborative_webcrawler_server.parse_html.webofscience import extract_articles as extract_articles_from_webofscience
from collaborative_webcrawler_server.parse_html.sciencedirect import extract_article_info as extract_article_info_from_sciencedirect
from collaborative_webcrawler_server.scraper import Scraper, PopularScraper, SeedScraper, KeywordScraper
from collaborative_webcrawler_server.db import Database

APP_NAME = __package__.split('.')[0]
config_file = Path(user_config_dir(APP_NAME)) / "config.json"
if config_file.exists() and (data := config_file.read_text()):
    config = json.loads(data)
else:
    config = {}

try:
    data_dir = Path(config.get("db_dir"))
except TypeError:
    data_dir = Path(user_config_dir(APP_NAME))
    config["db_dir"] = data_dir
    config_file.write_text(json.dumps(config))
db_path = data_dir / "pages.db"
db_path.parent.mkdir(exist_ok=True)
db = Database(db_path)

app = Flask(__name__)
CORS(app)  # allow cross-origin requests from extension
VALID_SESSION_ID = None

_temp_dir = tempfile.TemporaryDirectory(prefix=f"{APP_NAME}-")
SNAPSHOT_DIR = Path(_temp_dir.name) / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

# prevent DoS with limit on number of elements and dropping old requests if you want
current_requests = {}

# scraper = SeedScraper(44949177276, 34547969777, db=db)
# scraper = Scraper(db=db)
# scraper = SeedScraper(85042551265, db=db)

# scraper = KeywordScraper([
    # "shared control teleoperation",
    # "policy blending teleoperation",
    # "assisted teleoperation",
    # "shared autonomy teleoperation",
    # "time delay teleoperation",
    # "goal teleoperation",
    # "intent teleoperation",
    # "intention teleoperation",
    # "arbitration teleoperation",
    # "shared-control telemanipulation",
    # "policy blending telemanipulation",
    # "assisted telemanipulation",
    # "shared autonomy telemanipulation",
    # "goal telemanipulation",
    # "intent telemanipulation",
    # "intention telemanipulation",
    # "arbitration telemanipulation",
    # "arbitration shared-control",
    # "\"Position predictions\" teleoperation",
    # "\"motion prediction\" teleoperation",
    # "prediction teleoperation",
    # "movement intention prediction",
    # "model \"shared control\"",
    # "freeform teleoperation",
    # "\"free motion\" teleoperation",
    # "intention \"shared control\""
    # "\"policy adaptation\" teleoperation"
# ], db=db)

scraper = SeedScraper(85018894393, 84879913764, 84879038379, db=db)

def save_snapshot(payload):
    # Save snapshot to disk for inspection
    html = payload.get("html", "")
    meta = payload.get("meta", {})
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    url_safe = meta.get("url", "unknown").replace(":", "_").replace("/", "_")[:80]
    fname = f"{timestamp}_{url_safe}.html"
    path = os.path.join(SNAPSHOT_DIR, fname)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<!-- saved: {datetime.utcnow().isoformat()} UTC -->\n")
            f.write(html)
        # print(f"[SNAPSHOT] Saved HTML snapshot to {path}")
        return path
    except Exception as e:
        print(f"[SNAPSHOT] Error saving HTML snapshot: {e}")
        raise e

def delete_file(path):
    try:
        abs_path = os.path.abspath(path)
        if abs_path.startswith(SNAPSHOT_DIR):
            os.remove(abs_path)
            # print(f"[CLEANUP] Deleted snapshot {abs_path}")
        else:
            print(f"[CLEANUP] Skipped deletion (outside SNAPSHOT_DIR): {abs_path}")
    except Exception as e:
        print(f"[CLEANUP] Could not delete {path}: {e}")

def extract_articles(payload, path):
    meta = payload.get("meta", {})
    domain = meta.get("domain", "unknown")
    print(domain)
    try:
        # Load the data from a single paper
        if domain in ["www.sciencedirect.com"]:
            articles = [extract_article_info_from_sciencedirect(path)]

        # Get info of list of papers
        elif domain == "www.webofscience.com":
            articles = extract_articles_from_webofscience(path)
        elif domain == "www.scopus.com":
            articles = extract_articles_from_scopus(path)
        print(f"[PARSE] Extracted {len(articles)} article(s) from {meta.get('url')}")
    except Exception as e:
        print(f"[PARSE] Error parsing page {meta.get('url')}: {e}")

    return articles

@app.route("/receive", methods=["POST"])
def receive():
    instructions = []

    payload = request.get_json(force=True)
    token = payload.get("token")
    
    path = save_snapshot(payload) # I could use a `with ... as` to make sure the file is deleted immediately even in case of crash, but it's nice to debug if I can still read them.
    articles = extract_articles(payload, path)

    if token in current_requests: # if None should still return False
        next_page, requested_article, request_type = current_requests[token] # Keep old page in case page is corrupted
    
        if articles is None: # Corrupted page -> request again
            return jsonify({"status": "ok", "instructions": [{"type": "redirect", "url": next_page}]})

        del current_requests[token]

        for article in articles:
            # Should we save in the scraper since that's where we update it ?
            # if article.id not in scraper.known_articles: # TODO Check that num_citing hasn't change
            #     db.save_page(article)    
            scraper.update(article)
            if request_type == "CITING" and article.id not in requested_article.citing: 
                requested_article.citing.append(article.id)
            elif request_type == "CITED" and article.id not in requested_article.cited:
                requested_article.cited.append(article.id)

        if request_type == "CITING":
            # assert len(requested_article.citing) - requested_article.num_citing < 5 or len(requested_article.citing) % 200 < 5, requested_article # This break when we have an update
            if len(requested_article.citing) > requested_article.num_citing:
                requested_article.num_citing = len(requested_article.citing)
            db.update_page(requested_article)
        if request_type == "CITED": # TODO continue if there are multiple pages. For now I trust the scraper to continue
            # Make it try again instead of dying 
            # if len(requested_article.cited) == 0:
            #     print("ERROR LOADING PAGE")
            #     scraper.update(requested_article) # Repeat if you missed a page
            # else:
            requested_article.num_cited = len(requested_article.cited)
            requested_article.explored = True
            db.update_page(requested_article)
        if article.id not in scraper.known_articles:
            db.save_page(article)

    else:
        if articles is not None:
            for article in articles:
                scraper.update(article)
                db.update_page(article)

    delete_file(path)

    next_page = scraper.next_target # Will update the state and current article 
    # TODO handle job done
    # if next_page is None:
    #     instructions = +[
    #         {
    #             "type": "insert_html",
    #             "selector": "body",
    #             "position": "afterbegin",
    #             "html": (
    #                 "<div id='server-banner' "
    #                 "style='position:fixed;left:0;right:0;top:0;background:#fffae6;"
    #                 "padding:8px;border-bottom:1px solid #e6db9a;z-index:99999;'>"
    #                 "Thank you, but no pages are needed at the moment</div>"
    #             )
    #         }
    #     ]
    #     return jsonify({"status": "ok", "instructions": instructions})
    requested_article = scraper.current_article
    request_type = scraper.state # Looking for citations or references
    request_token = secrets.token_hex(8)
    current_requests[request_token] = (next_page, requested_article, request_type)

    instructions += [
            {"type": "set_token", "token": request_token}
        ]

    instructions += [
        {
            "type": "redirect",
            "url": next_page
        }
    ]

    # Not implemented yet
    # if scraper.save_zotero:
    #     instruction += {
    #         "type": "zotero_save"
    #     }

    return jsonify({"status": "ok", "instructions": instructions})

if __name__ == "__main__":
    try:
        print("[SERVER] Starting server on 127.0.0.1:5000")
        app.run(host="127.0.0.1", port=5000)
    finally:
        _temp_dir.cleanup()