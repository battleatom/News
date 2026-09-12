#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
TAG = '<script src="assets/entertainment-v4.js?v=1"></script>'


def main():
    text = INDEX.read_text(encoding="utf-8")
    if TAG in text:
        print("Entertainment V4 UI already wired.")
        return
    if "</body>" not in text:
        raise SystemExit("index.html is missing </body>")
    text = text.replace("</body>", f"\n{TAG}\n</body>", 1)
    INDEX.write_text(text, encoding="utf-8")
    print("Entertainment V4 UI injected into index.html")


if __name__ == "__main__":
    main()
