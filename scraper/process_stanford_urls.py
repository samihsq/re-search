#!/usr/bin/env python3
"""
process_stanford_urls.py – Validate a batch of Stanford research URLs and
(optionally) update the RESEARCH_URLS list inside backend/app/config.py.

Usage:
  # Dry-run: just analyse the URLs and print a JSON report
  python backend/process_stanford_urls.py /path/to/stanford_research_urls_100.txt

  # Analyse and patch backend/app/config.py automatically
  python backend/process_stanford_urls.py /path/to/stanford_research_urls_100.txt --update-config

The script performs three steps:
 1. Read URLs from the supplied text file (one URL per line, comments allowed).
 2. Re-use URLValidator to test connectivity + presence of specific opportunity pages.
 3. Emit a concise JSON report with actionable lists and, if requested, patch
    the RESEARCH_URLS list in backend/app/config.py.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import List, Set, Dict, Any

import aiohttp

# Gemma / Google Gemini HTML parsing service
from app.services.llm_validation_service import LLMHtmlParsingService
# Optional progress bar (tqdm). Falls back gracefully if not installed.
try:
    from tqdm import tqdm  # type: ignore
except ImportError:  # pragma: no cover
    tqdm = None

# The validator lives one directory above this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(SCRIPT_DIR))  # Ensure scraper package is importable

from url_validator import URLValidator  # noqa: E402 – after sys.path tweak
from app.config import RESEARCH_URLS  # Access default list

CONFIG_PATH = PROJECT_ROOT / "scraper" / "app" / "config.py"


def load_urls(file_path: Path) -> List[str]:
    """Load URLs from a text file, ignoring blanks and lines that start with #."""
    raw_lines = file_path.read_text().splitlines()
    urls = [line.strip() for line in raw_lines if line.strip() and not line.strip().startswith("#")]
    return urls


async def validate_urls(urls: List[str]):
    """Run URLValidator on the provided list and return its generated report."""
    async with URLValidator() as validator:
        results = await validator.validate_all_urls(urls)
        report = validator.generate_report(results)
    return report


# ================================================================
# Gemma LLM deep-discovery helpers (must be defined before main())
# ================================================================


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch HTML content with a short timeout. Returns empty string on failure."""
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return ""


async def deep_llm_discovery(start_urls: List[str], max_depth: int = 2) -> Dict[str, Dict[str, Any]]:
    """Use Gemma LLM to iteratively extract opportunity links until reaching specific pages.

    Returns mapping {root_url: { "count": int, "links": [urls] }}
    """
    llm_service = LLMHtmlParsingService()
    if not llm_service.client:
        print("⚠️  Gemma client unavailable – skipping deep LLM extraction.")
        return {}

    results: Dict[str, Dict[str, Any]] = {}

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (Stanford Research Bot)"}) as session:

        async def process_root(root_url: str):
            visited: Set[str] = set()
            final_links: Set[str] = set()

            queue: List[tuple[str, int]] = [(root_url, 0)]

            while queue:
                current_url, depth = queue.pop(0)
                if current_url in visited or depth > max_depth:
                    continue
                visited.add(current_url)

                html = await fetch_html(session, current_url)
                if not html:
                    continue

                parse_result = await llm_service.parse_html_content(html, current_url)
                opps = parse_result.get("opportunities", []) if parse_result.get("success") else []

                # If no structured opportunities returned, treat page as non-opportunity
                if not opps:
                    continue

                # Heuristic: if the page contains multiple opportunities, treat it as list page
                if len(opps) > 1 and depth < max_depth:
                    for opp in opps:
                        app_url = opp.get("application_url") or current_url
                        if app_url and app_url not in visited:
                            queue.append((app_url, depth + 1))
                else:
                    # Assume this page is a concrete opportunity page
                    final_links.add(current_url)

            results[root_url] = {"count": len(final_links), "links": sorted(final_links)}

        # Progress bar setup
        if tqdm:
            pbar = tqdm(total=len(start_urls), desc="Gemma LLM Discovery", unit="url")

            tasks = [asyncio.create_task(process_root(u)) for u in start_urls]

            for task in asyncio.as_completed(tasks):
                await task
                pbar.update(1)

            pbar.close()
        else:
            # Fallback: simple counter output
            completed = 0
            total = len(start_urls)

            async def wrap(u):
                nonlocal completed
                await process_root(u)
                completed += 1
                print(f"Processed {completed}/{total} ({u})")

            await asyncio.gather(*[wrap(u) for u in start_urls])

    return results


def patch_config(report: dict, dry_run: bool = False):
    """Update RESEARCH_URLS in backend/app/config.py according to the report.

    • Remove everything in report["actions"]["urls_to_remove"]
    • Remove high-level pages in report["actions"]["urls_to_replace_with_specific"]
    • Add each URL in report["actions"]["sub_urls_to_add"]
    """
    urls_to_remove: Set[str] = set(report["actions"].get("urls_to_remove", []))
    urls_to_replace: Set[str] = set(report["actions"].get("urls_to_replace_with_specific", []))
    sub_urls_to_add: Set[str] = set(report["actions"].get("sub_urls_to_add", []))

    target_urls_to_delete = urls_to_remove | urls_to_replace

    config_text = CONFIG_PATH.read_text()

    # Simple, safe replacement: find the RESEARCH_URLS list with regex, parse it, modify, re-dump
    pattern = re.compile(r"RESEARCH_URLS\s*=\s*\[(.*?)]", re.S)
    match = pattern.search(config_text)
    if not match:
        raise RuntimeError("Could not locate RESEARCH_URLS list in config.py")

    # Evaluate the list literal safely using ast.literal_eval on the matched string
    import ast

    current_list_literal = "[" + match.group(1) + "]"
    current_urls: List[str] = ast.literal_eval(current_list_literal)

    # Apply removals and additions
    updated_urls: Set[str] = set(current_urls) - target_urls_to_delete
    updated_urls |= sub_urls_to_add

    # Keep list sorted & stable
    final_urls = sorted(updated_urls)

    # Build replacement string with proper indentation (4 spaces) & trailing comma for each
    indent = " " * 4
    new_list_lines = ["RESEARCH_URLS = [\n"] + [f"{indent}\"{url}\",\n" for url in final_urls] + ["]"]
    new_list_literal = "".join(new_list_lines)

    new_config_text = pattern.sub(new_list_literal, config_text)

    if dry_run:
        print("\n=== DRY RUN: updated RESEARCH_URLS would look like ===\n")
        print(new_list_literal)
        print("\n=== End DRY RUN ===\n")
    else:
        CONFIG_PATH.write_text(new_config_text)
        print(f"✅ backend/app/config.py updated – total URLs now: {len(final_urls)}")


async def main(args):
    # Determine URL source: file or config list
    if args.url_file and args.url_file.lower() != "config":
        url_file_path = Path(args.url_file)
        if not url_file_path.is_file():
            print(f"Error: {url_file_path} is not a valid file path.")
            sys.exit(1)
        urls = load_urls(url_file_path)
        source_desc = str(url_file_path)
    else:
        urls = list(RESEARCH_URLS)
        source_desc = "app.config.RESEARCH_URLS"

    print(f"Loaded {len(urls)} URLs from {source_desc}. Beginning validation…")

    report = await validate_urls(urls)

    report_name = source_desc.replace('/', '_').replace('.', '_')
    timestamp = Path(f"url_validation_report_{report_name}.json")
    timestamp.write_text(json.dumps(report, indent=2))
    print(f"Validation complete – report saved to {timestamp.resolve()}")

    actions = report.get("actions", {})
    print("\nSummary of actions:")
    print(f"  • URLs to remove: {len(actions.get('urls_to_remove', []))}")
    print(f"  • URLs to replace with specific pages: {len(actions.get('urls_to_replace_with_specific', []))}")
    print(f"  • New sub-URLs to add: {len(actions.get('sub_urls_to_add', []))}\n")

    # ------------------------------------------------------------------
    # Optional Gemma-powered deep opportunity extraction
    # ------------------------------------------------------------------
    if args.deep_llm:
        print("🔎 Running Gemma LLM extraction – this may take a while…\n")
        llm_results = await deep_llm_discovery(urls)

        for root_url, data in llm_results.items():
            print(f"{root_url} → {data['count']} opportunity link(s) found:")
            for link in data["links"]:
                print(f"   • {link}")
            print()

    if args.update_config:
        patch_config(report, dry_run=False)
    else:
        print("Run again with --update-config to automatically patch backend/app/config.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Stanford research URLs. If no url_file is given (or 'config' is passed), the script uses RESEARCH_URLS from app.config. Optionally patch config.py and discover real links via Gemma.")
    parser.add_argument("url_file", nargs="?", default="config", help="Path to a text file of URLs OR 'config' to use the list in app.config (default). Ignored when --apply-report is used.")
    parser.add_argument("--apply-report", metavar="REPORT_JSON", help="Patch backend/app/config.py using an existing validation report (skips validation phase)")
    parser.add_argument("--update-config", action="store_true", help="Patch backend/app/config.py with the validation results")
    parser.add_argument("--deep-llm", action="store_true", help="Use Gemma LLM to extract opportunities & drill down to real application links (slow)")

    args = parser.parse_args()

    if args.apply_report:
        # Load report from provided JSON and patch config immediately
        report_path = Path(args.apply_report)
        if not report_path.is_file():
            print(f"Error: {report_path} is not a valid file path.")
            sys.exit(1)
        report_data = json.loads(report_path.read_text())
        patch_config(report_data, dry_run=False)
    else:
        asyncio.run(main(args)) 