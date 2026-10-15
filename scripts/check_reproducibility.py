#!/usr/bin/env python3
"""
Prove the dataset is reproducible: regenerate it with the seed recorded in
data/raw/manifest.json into a temporary directory and compare SHA-256
hashes file by file with the committed manifest.

Exit code 0 = identical, 1 = mismatch.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "data" / "raw" / "manifest.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_dataset.py"),
                        "--seed", str(manifest["seed"]), "--out", tmp],
                       check=True, capture_output=True)
        fresh = json.loads((Path(tmp) / "raw" / "manifest.json").read_text())
    ok = True
    for name, meta in manifest["files"].items():
        same = fresh["files"][name]["sha256"] == meta["sha256"]
        ok &= same
        print(f"{'OK  ' if same else 'DIFF'} {name:26s} {meta['sha256'][:16]}...")
    print("Reproducible: identical output for seed", manifest["seed"] if ok else "")
    if not ok:
        print("NOT reproducible - committed files differ from a fresh run.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
