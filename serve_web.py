"""Serve the self-contained web project; no package installation is required."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote
import threading
import webbrowser
from stream import ROOT


class ProjectHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Download aliases avoid including another copy of the raw data in dist.
        clean = path.split("?", 1)[0]
        report_name = "481013386_MohammedKhalifah_5113_Assignment_1.pdf"
        report = ROOT / "output" / "pdf" / report_name
        if not report.exists():
            report = ROOT / report_name  # The submission ZIP places it at root.
        aliases = {"/downloads/NASA_access_log_Jul95.gz": ROOT / "data" / "NASA_access_log_Jul95.gz",
            "/downloads/report.pdf": report}
        if clean in aliases:
            return str(aliases[clean])
        if clean.startswith("/downloads/results/"):
            target = (ROOT / "results" / unquote(clean[len("/downloads/results/"):])).resolve()
            if target.is_relative_to((ROOT / "results").resolve()):
                return str(target)
        return super().translate_path(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    handler = partial(ProjectHandler, directory=str(ROOT / "web" / "dist"))
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        url = f"http://{args.host}:{args.port}"
        print(f"StreamLab is ready: {url}\nPress Ctrl+C to stop.", flush=True)
        if args.open:
            threading.Timer(0.5, webbrowser.open, args=[url]).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
