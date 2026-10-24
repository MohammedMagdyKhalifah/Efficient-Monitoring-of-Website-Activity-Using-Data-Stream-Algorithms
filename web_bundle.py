"""Sync web downloads/source explorer and build a completely offline HTML app."""
import base64
import json
import mimetypes
from pathlib import Path
import shutil
from stream import ROOT, DATA

DIST = ROOT / "web" / "dist"
REPORT_NAME = "481013386_MohammedKhalifah_5113_Assignment_1.pdf"


def sync():
    sources = {str(p.relative_to(ROOT)): p.read_text() for p in sorted(ROOT.glob("*.py"))}
    for parent, suffixes in [(ROOT / "tests", {".py"}), (ROOT / "web", {".md", ".json", ".mjs"}),
                              (DIST, {".js", ".html", ".css", ".svg"})]:
        for p in sorted(parent.rglob("*")):
            if p.is_file() and p.suffix in suffixes and not any(part in {".git", ".openai", "node_modules", "downloads", "data", "__pycache__"} for part in p.relative_to(parent).parts):
                sources[str(p.relative_to(ROOT))] = p.read_text()
    (DIST / "data" / "sources.json").write_text(json.dumps(sources, separators=(",", ":")))
    downloads = DIST / "downloads"
    downloads.mkdir(exist_ok=True)
    shutil.copyfile(DATA, downloads / DATA.name)
    report = ROOT / "output" / "pdf" / REPORT_NAME
    if not report.exists():
        report = ROOT / REPORT_NAME
    if report.exists():
        shutil.copyfile(report, downloads / "report.pdf")
    files = [dict(name=name, content=value) for name, value in sources.items() if not name.startswith("web/dist/")]
    for name in ["README.md", "WEB_README.md", "ORAL_NOTES_AR.md", "requirements.txt", "references.bib", "data/README.md", "data/manifest.json"]:
        p = ROOT / name
        if p.exists():
            files.append(dict(name=name, content=p.read_text()))
    files.append(dict(name=f"data/{DATA.name}", url=f"./downloads/{DATA.name}"))
    if report.exists():
        files.append(dict(name=REPORT_NAME, url="./downloads/report.pdf"))
    result_dir = downloads / "results"
    result_dir.mkdir(exist_ok=True)
    for p in sorted((ROOT / "results").rglob("*")):
        if p.is_file() and p.suffix in {".csv", ".json", ".txt", ".png"}:
            dest = result_dir / p.relative_to(ROOT / "results")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
            files.append(dict(name=str(p.relative_to(ROOT)), url="./downloads/results/"+str(p.relative_to(ROOT / "results"))))
    # Include the index by URL; its finite contents do not recursively embed it.
    index = DIST / "data" / "project-files.json"
    index.write_text("[]")
    for p in sorted(DIST.rglob("*")):
        if p.is_file() and "downloads" not in p.relative_to(DIST).parts:
            files.append(dict(name="web/dist/"+str(p.relative_to(DIST)), url="./"+str(p.relative_to(DIST))))
    index.write_text(json.dumps(files, separators=(",", ":")))
    return files


def offline():
    assets = {}
    for p in DIST.rglob("*"):
        if not p.is_file() or p.name in {"index.html", "app.js", "styles.css", "worker.js", "algorithms.js", "download.js"}:
            continue
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        assets[str(p.relative_to(DIST))] = "data:"+mime+";base64,"+base64.b64encode(p.read_bytes()).decode()
    # These code files must remain downloadable in a generated project ZIP.
    for name in ["index.html", "app.js", "styles.css", "worker.js", "algorithms.js", "download.js"]:
        assets[name] = "data:text/plain;base64,"+base64.b64encode((DIST / name).read_bytes()).decode()
    worker_assets = {name: value for name, value in assets.items() if name.startswith("data/") and name.endswith(".gz") and "catalog" not in name}
    fetch_adapter = """const originalFetch = self.fetch.bind(self); self.fetch = (input, options) => {
      const path = String(input).replace(/^\\.\\//, '');
      return originalFetch(ASSETS[path] || input, options);
    };"""
    engine = (DIST / "algorithms.js").read_text().replace("export ", "")
    worker = (DIST / "worker.js").read_text().replace("import {StreamEngine} from './algorithms.js';", "")
    worker = worker.replace("if(data.type==='init') return init(data.config);",
        "if(data.type==='init') { ASSETS = data.assets || ASSETS; return init(data.config); }")
    worker_code = "let ASSETS={};"+fetch_adapter+engine+worker
    app = (DIST / "app.js").read_text().replace("import {downloadProject} from './download.js';", "")
    download = (DIST / "download.js").read_text().replace("export ", "")
    worker_line = "new Worker('./worker.js',{type:'module'})"
    replacement = "new Worker(URL.createObjectURL(new Blob(["+json.dumps(worker_code)+"],{type:'text/javascript'})))"
    assert worker_line in app
    app = app.replace(worker_line, replacement)
    app = app.replace("worker.postMessage({type:'init',config});",
        "worker.postMessage({type:'init',config,assets:WORKER_ASSETS});")
    worker_asset_keys = list(worker_assets)
    app = "const WORKER_ASSETS=Object.fromEntries("+json.dumps(worker_asset_keys)+".map(k=>[k,ASSETS[k]]));"+app
    link_adapter = """for (const link of document.querySelectorAll('[data-embedded-href]')) {
      originalFetch(ASSETS[link.dataset.embeddedHref]).then(r=>r.blob()).then(b=>{link.href=URL.createObjectURL(b);});
    }"""
    bundle = "const ASSETS="+json.dumps(assets)+";"+fetch_adapter+link_adapter+download+app
    html = (DIST / "index.html").read_text()
    html = html.replace('<link rel="icon" href="./favicon.svg" type="image/svg+xml">', "")
    html = html.replace('<link rel="stylesheet" href="./styles.css">', "<style>"+(DIST / "styles.css").read_text()+"</style>")
    html = html.replace('<script type="module" src="./app.js"></script>', "<script>"+bundle+"</script>")
    # Native document links need embedded URLs in a file:// session too.
    html = html.replace('href="./downloads/report.pdf"', 'href="#" data-embedded-href="downloads/report.pdf"')
    html = html.replace('href="./data/parameter_sweep.csv"', 'href="#" data-embedded-href="data/parameter_sweep.csv"')
    target = ROOT / "output" / "StreamLab_Offline.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html)
    print(f"Offline app: {target} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    sync()
    offline()
