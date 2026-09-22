#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

def slugify(name: str) -> str:
    name = re.sub(r"^\.\[|\]$", "", name)
    name = re.sub(r"^\.", "", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-").lower()
    return name[:110] or "untitled"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("backup")
    ap.add_argument("output")
    args=ap.parse_args()
    data=json.loads(Path(args.backup).read_text(encoding="utf-8"))
    out=Path(args.output)
    (out/"core").mkdir(parents=True,exist_ok=True)
    (out/"reference").mkdir(parents=True,exist_ok=True)
    manifest=[]
    for i,s in enumerate(data["scripts"],1):
        folder=out/("core" if s.get("principal") else "reference")
        path=folder/f"{i:02d}-{slugify(s['name'])}.pine"
        path.write_text(s["source"],encoding="utf-8",newline="")
        manifest.append({
            "index":i,"name":s["name"],"principal":bool(s.get("principal")),
            "path":str(path.relative_to(out)),"tradingview_id":s.get("id"),
            "tradingview_version":s.get("version"),"stats":s.get("stats")
        })
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"exported {len(manifest)} scripts")

if __name__=="__main__":
    main()
