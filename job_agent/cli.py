"""python -m job_agent scan --since 2026-09-20 --out shortlist.md"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import build_shortlist
from .scoring import Profile, score_vacancy
from .telegram import fetch_channel

ROOT = Path(__file__).resolve().parent.parent


def load_profile(path: Path) -> Profile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Profile(**data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI job search agent: сбор и скоринг вакансий")
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan", help="собрать вакансии из Telegram-каналов и построить шортлист")
    scan.add_argument("--since", required=True, help="дата YYYY-MM-DD")
    scan.add_argument("--channels", default=str(ROOT / "config" / "channels.json"))
    scan.add_argument("--profile", default=str(ROOT / "config" / "profile.example.json"))
    scan.add_argument("--out", default="shortlist.md")
    args = parser.parse_args(argv)

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    profile = load_profile(Path(args.profile))
    channels = json.loads(Path(args.channels).read_text(encoding="utf-8"))["channels"]

    items = []
    for ch in channels:
        try:
            posts = fetch_channel(ch["name"], args.since)
        except Exception as exc:  # сеть, закрытый канал и т. п. — не роняем весь прогон
            print(f"{ch['name']}: ошибка {exc}", file=sys.stderr)
            continue
        print(f"{ch['name']}: {len(posts)} постов", file=sys.stderr)
        items += [(p, score_vacancy(p.text, profile)) for p in posts if p.text]

    Path(args.out).write_text(build_shortlist(items), encoding="utf-8")
    print(f"Готово: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
