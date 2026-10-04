import argparse
import json
import logging
import os
import secrets
from urllib.parse import parse_qsl, urlsplit

from flask import Flask, request, jsonify
from flask_cors import CORS

from collaborative_scraper.config import config_path
from collaborative_scraper.parse_html.parser import extract_elements
from collaborative_scraper.registry import get_registry
from collaborative_scraper.scrapers.base import FETCHRequest, POSTRequest, Request, is_done
from collaborative_scraper.scrapers.scraper import generate_scraper, scraper_config, supported_targets
from collaborative_scraper.utils import get_project_dir, save_snapshot

logger = logging.getLogger(__name__)

def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.WARNING),
        format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def create_app(target: str) -> Flask:
    """Build a Flask app serving one target. Importing this module no longer
    parses arguments or builds a scraper, so tests can call it directly."""
    app = Flask(__name__)
    CORS(app)  # allow cross-origin requests from extension

    project_name = target.split(":")[0]
    scraper = generate_scraper(target)
    current_requests = {}  # token -> RequestData

    def assign(next_request, request_data) -> list[dict]:
        """Hand a request to the client: a fresh token plus the request's own instruction."""
        if not isinstance(next_request, Request):
            raise TypeError(f"expected GETRequest, POSTRequest, FETCHRequest or None, "
                            f"got {type(next_request).__name__}")
        # Kept with the fetch: the parser needs a POST's form when the page
        # returns, /fetch_result needs a FETCH's callback.
        request_data.request = next_request
        request_token = secrets.token_hex(8)
        current_requests[request_token] = request_data
        logger.info("[ASSIGNMENT] %s -> %s", request_token, next_request)
        return [{"type": "set_token", "token": request_token}, next_request.instruction()]

    def next_instructions(request_data) -> list[dict]:
        """Ask the scraper for the next request, or tell the client the crawl is over."""
        next_request, request_data = scraper.generate_request(request_data)
        if next_request is None:
            # Standardized banner command: the client owns the styling, the
            # server only sends a message and a level ("info" | "error").
            return [{
                "type": "banner",
                "level": "info",
                "message": "Thank you, but no more pages are needed at the moment",
            }]
        return assign(next_request, request_data)

    @app.route("/ping", methods=["GET"])
    def ping():
        # Lightweight health check the client pings on connect to confirm the
        # server is up and working.
        return jsonify({"status": "ok"})

    @app.route("/fetch_result", methods=["POST"])
    def receive_fetch():
        """The response to a FETCH instruction: ``{token, status, body}``.

        ``body`` is the raw response text. The FETCHRequest's callback turns its
        JSON into the next request for the same fetch; when there is none (the
        callback returned None, or the fetch failed) the scraper picks the next
        one, so a single bad lookup never stalls the client.
        """
        payload = request.get_json(force=True)
        token = payload.get("token")
        request_data = current_requests.pop(token, None)
        fetch = None if request_data is None else request_data.request
        if not isinstance(fetch, FETCHRequest):
            # Unknown token (e.g. the server restarted) or not a FETCH: there is
            # no callback to run, so just move the client on.
            logger.warning("fetch result for unknown token %r; ignoring it", token)
            return jsonify({"status": "ok", "instructions": next_instructions(None)})

        next_request = None
        status = payload.get("status")
        if not isinstance(status, int) or not 200 <= status < 300:
            logger.warning("%s failed with status %r; skipping it", fetch, status)
        else:
            try:
                data = json.loads(payload.get("body", ""))
            except ValueError:
                logger.warning("%s did not return JSON; skipping it", fetch, exc_info=True)
            else:
                try:
                    next_request = fetch.callback(data, request_data)
                except Exception:
                    # Same policy as a parser failure: crash in DEBUG, carry on otherwise.
                    if logger.isEnabledFor(logging.DEBUG):
                        raise
                    logger.warning("callback of %s failed; skipping it", fetch, exc_info=True)

        if next_request is None:
            return jsonify({"status": "ok", "instructions": next_instructions(request_data)})
        return jsonify({"status": "ok", "instructions": assign(next_request, request_data)})

    @app.route("/receive", methods=["POST"])
    def receive():
        instructions = [] # Commands to send back to the client

        payload = request.get_json(force=True)
        token = payload.get("token")
        can_redirect = payload.get("allow_redirect", True)
        meta = payload.get("meta", {})
        html_page = payload.get("html", "")
        url = meta.get("url", "")

        request_data = current_requests.get(token)
        get_parameters = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
        # Only a page the server asked the client to POST has a form to report.
        post_parameters = None
        if request_data is not None and isinstance(request_data.request, POSTRequest):
            post_parameters = request_data.request.parameters

        try:
            result = extract_elements(html_page, url, get_parameters, post_parameters)
            if result is not None:
                result.url = url
            elements = None if result is None else result.elements
        except Exception as e:
            # In DEBUG the page that broke the parser is worth more than
            # uptime: dump it next to the project's data and let it crash.
            if logger.isEnabledFor(logging.DEBUG):
                path = save_snapshot(payload, get_project_dir(project_name))
                logger.critical(f"could not parse elements. Page saved to {path}")
                raise e
            else:
                logger.warning("could not parse elements", exc_info=True)
                elements = None

        if request_data is None:
            # Page the client navigated to on its own. If it didn't parse
            # (parser returns None for a page that wasn't fully loaded) there is
            # nothing to record, so skip rather than crash unknown_page.
            if elements is not None:
                scraper.unknown_page(result)
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

            request_data.result = result # the page's metadata, for update / next_state / success
            for element in elements:
                scraper.update(element, request_data)
            request_data.fetch_phase = scraper.next_state(request_data)

            if is_done(request_data.fetch_phase):
                scraper.success(request_data)

        if can_redirect:
            instructions += next_instructions(request_data)
        else:
            logger.debug("User doesn't want to redirect")

        return jsonify({"status": "ok", "instructions": instructions})

    return app

def _targets_epilog(registry, targets) -> str:
    if not targets:
        return ("no targets available: no plugin is installed.\n"
                "Install one (pip install collaborative-scraper-<name>) "
                "or see --list-plugins.")
    lines = [f"  {t:40} ({registry.owner(t)})" for t in targets]
    return "available targets:\n" + "\n".join(lines)

def _resolve_target(parser, args, targets) -> str:
    """The project can be given positionally or with --project, not both."""
    if args.project_pos and args.project and args.project_pos != args.project:
        parser.error(f"project given twice: {args.project_pos!r} and {args.project!r}")
    target = args.project or args.project_pos
    if target is None:
        parser.error("no project given.\n" + _targets_epilog(get_registry(), targets))
    return target

def _get_parser(epilog, choices) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collaborative_scraper",
        description="Server coordinating distributed webcrawling.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_pos", nargs="?", metavar="project",
                        choices=choices or None,
                        help="target to run, as project:variant")
    parser.add_argument("--project", default=None, metavar="project",
                        choices=choices or None,
                        help="same as the positional argument")
    parser.add_argument("--info", action="store_true",
                        help="print the resolved database path and exit")
    parser.add_argument("--list-plugins", action="store_true",
                        help="print installed plugins and their versions")
    parser.add_argument("--list-targets", action="store_true",
                        help="print every target and the plugin providing it")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    return parser

def main(argv=None) -> None:
    configure_logging()

    # Discovery must happen before the parser is built: choices= comes from it.
    registry = get_registry()
    targets = supported_targets()
    epilog = _targets_epilog(registry, targets)

    parser = _get_parser(epilog, targets)
    args = parser.parse_args(argv)

    if args.list_plugins:
        for name, version in sorted(registry.plugins.items()):
            print(f"{name} {version}")
        return
    if args.list_targets:
        print(epilog)
        return

    target = _resolve_target(parser, args, targets)

    if args.info:
        # The database lives inside the project folder: print the folder once
        # and the database relative to it, rather than repeating the prefix.
        project_dir = get_project_dir(target.split(':')[0])
        db_file = scraper_config(target)["db_file"]
        print(f"project folder located at: {project_dir}")
        print(f"database for {target}: {db_file.relative_to(project_dir)} (in the project folder)")
        print(f"config file located at: {config_path()}")
        return

    logger.info("[SERVER] Starting server on %s:%d", args.host, args.port)
    create_app(target).run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()