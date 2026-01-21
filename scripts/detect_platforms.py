#!/usr/bin/env python3
"""
Detect whether companies use Greenhouse or SmartRecruiters by probing public APIs.

This uses slug heuristics (no guaranteed coverage). Results are saved to
platform_matches.json in the repo root for easy review.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Iterable

import requests


COMPANIES = [
    "xAI",
    "Safe Superintelligence",
    "Anthropic",
    "Mistral AI",
    "Unconventional AI",
    "Anysphere",
    "Reflection AI",
    "Skild AI",
    "Mercor",
    "Physical Intelligence",
    "Perplexity",
    "Sierra",
    "Cognition",
    "Thinking Machines Lab",
    "The Bot Company",
    "Eon",
    "Lovable",
    "OpenAI",
    "ElevenLabs",
    "Harvey",
    "Surge AI",
    "Black Forest Labs",
    "Helsing",
    "Ramp",
    "OpenEvidence",
    "Together",
    "Bilt",
    "Anduril",
    "Decagon",
    "Periodic Labs",
    "Whatnot",
    "Poolside",
    "Figure",
    "Decart",
    "Base",
    "Saronic",
    "Revolut",
    "Fireworks",
    "Sakana AI",
    "Liquid AI",
    "Deel",
    "Hippocratic AI",
    "Luma AI",
    "Xaira",
    "Fal",
    "Plata",
    "Cambricon",
    "Supabase",
    "LMArena",
    "Tether",
    "Pantheon",
    "Crusoe",
    "Applied Intuition",
    "Kalshi",
    "Legora",
    "FieldAI",
    "Glean",
    "Databricks",
    "Astera Labs",
    "World Labs",
    "Beacon Software",
    "Chainguard",
    "Suno",
    "VAST Data",
    "Pinduoduo",
    "Cerebras Systems",
    "Pennylane",
    "DoorDash",
    "Runway",
    "Harmonic",
    "CoreWeave",
    "Nubank",
    "Devoted Health",
    "Abridge",
    "AppLovin",
    "Robinhood",
    "Lila Sciences",
    "Hygon",
    "Rippling",
    "Moonshot AI",
    "Temporal",
    "BaseTen",
    "Neuralink",
    "LangChain",
    "Genspark",
    "Figure",
    "Distyl",
    "Island",
    "Function Health",
    "Crescendo",
    "Flatpay",
    "Sonar",
    "Cohere",
    "Tabby",
    "Zepto",
    "Cyera",
    "ByteDance",
    "Pathos",
    "NewLimit",
    "Firmus",
    "Quince",
    "Vast",
    "Rivos",
    "Keep",
    "Wayve",
    "Harness",
    "Pacific Fusion",
    "Eve",
    "IREN",
    "Flock Safety",
    "Polymarket",
    "Abnormal AI",
    "Dream Games",
    "Celestial AI",
    "C6 Bank",
    "Kakao",
    "Aligned Data Centers",
    "Napster",
    "Pomelo Care",
    "bolttech",
    "PhonePe",
    "Zip",
    "Replit",
    "CATL",
    "Rapyd",
    "Upgrade",
    "Boring Company",
    "Gamma",
    "Tessl",
    "/dev/agents",
    "David AI",
    "BeZero",
    "Nirvana Insurance",
    "Dream Security",
    "Stripe",
    "Razor Group",
    "Coalition",
    "Samsara",
    "CrowdStrike",
    "Krutrim",
    "Wonder",
    "ClickHouse",
    "Coinbase",
    "Skims",
    "n8n",
    "Snowflake",
    "Trade Republic",
    "Fuse Energy",
    "Substrate",
    "Reka",
    "Orchard",
    "Apex",
    "Xpanceo",
    "Uber",
    "Motif",
    "Roivant Sciences",
    "Bullish",
    "Cribl",
    "Telegram",
    "Zetwerk",
    "Augment",
    "Canva",
    "Verkada",
    "DualEntry",
    "Vanta",
    "Vercel",
    "CloudKitchens",
    "Aven",
    "Writer",
    "IonQ",
    "Hadrian",
    "Discord",
    "Upwind",
    "Synthesia",
    "Onebrief",
    "Redwood Materials",
    "BharatPe",
    "Raise",
    "Qonto",
    "Rubrik",
    "Xiaomi",
    "Stoke Space",
    "EvenUp",
    "D-Matrix",
    "Contextual AI",
    "1X",
    "You.com",
    "Varda",
    "ShopMy",
    "Chapter",
    "Reducto",
    "PsiQuantum",
    "Mercury",
    "Statsig",
    "Meta",
    "Tesla",
    "SoFi",
    "Uala",
    "Modal Labs",
    "Jeeves",
]


def build_slug_candidates(name: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", name)
    if not words:
        return []

    original_no_space = "".join(words)
    title_no_space = "".join(w.capitalize() for w in words)
    lower_no_space = "".join(w.lower() for w in words)
    lower_hyphen = "-".join(w.lower() for w in words)
    lower_underscore = "_".join(w.lower() for w in words)

    candidates = [
        original_no_space,
        title_no_space,
        lower_no_space,
        lower_hyphen,
        lower_underscore,
    ]
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def check_greenhouse(session: requests.Session, slug: str) -> bool:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        resp = session.get(url, params={"per_page": 1}, timeout=10)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return isinstance(data, dict) and "jobs" in data
    except Exception:
        return False


def check_smartrecruiters(session: requests.Session, slug: str) -> bool:
    url = f"https://careers.smartrecruiters.com/{slug}"
    try:
        resp = session.get(url, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return False
        final_url = resp.url.rstrip("/")
        expected = f"https://careers.smartrecruiters.com/{slug}".rstrip("/")
        return final_url.lower() == expected.lower()
    except Exception:
        return False


def first_match(
    session: requests.Session,
    name: str,
    candidates: Iterable[str],
    check_fn,
    sleep_s: float = 0.2,
) -> str | None:
    for slug in candidates:
        if check_fn(session, slug):
            return slug
        time.sleep(sleep_s)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect Greenhouse/SmartRecruiters companies.")
    parser.add_argument("--limit", type=int, default=None, help="Max companies to scan")
    parser.add_argument("--start", type=int, default=0, help="Start index in company list")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between requests")
    parser.add_argument("--output", default="platform_matches.json", help="Output JSON path")
    parser.add_argument("--resume", action="store_true", help="Resume and append to existing output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
    })

    output_path = Path(args.output)
    if args.resume and output_path.exists():
        with output_path.open("r", encoding="utf-8") as f:
            results = json.load(f)
    else:
        results = {
            "greenhouse": [],
            "smartrecruiters": [],
            "unmatched": [],
        }

    scanned_names = set()
    for entry in results.get("greenhouse", []):
        scanned_names.add(entry.get("name"))
    for entry in results.get("smartrecruiters", []):
        scanned_names.add(entry.get("name"))
    for entry in results.get("unmatched", []):
        scanned_names.add(entry.get("name"))

    companies = COMPANIES[args.start:]
    if args.limit:
        companies = companies[: args.limit]

    for name in companies:
        if name in scanned_names:
            continue
        candidates = build_slug_candidates(name)
        gh_slug = first_match(session, name, candidates, check_greenhouse, sleep_s=args.sleep)
        sr_slug = first_match(session, name, candidates, check_smartrecruiters, sleep_s=args.sleep)

        if gh_slug:
            results["greenhouse"].append({"name": name, "slug": gh_slug})
        if sr_slug:
            results["smartrecruiters"].append({"name": name, "slug": sr_slug})
        if not gh_slug and not sr_slug:
            results["unmatched"].append({"name": name, "candidates": candidates})

        safe_name = name.encode("ascii", "backslashreplace").decode("ascii")
        print(f"{safe_name}: greenhouse={gh_slug or '-'} smartrecruiters={sr_slug or '-'}")

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved results to {output_path}")
    print(f"Greenhouse matches: {len(results['greenhouse'])}")
    print(f"SmartRecruiters matches: {len(results['smartrecruiters'])}")
    print(f"Unmatched: {len(results['unmatched'])}")


if __name__ == "__main__":
    main()
