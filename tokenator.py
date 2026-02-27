#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "humanfriendly>=10.0",
#     "rich>=14.3.3",
#     "tiktoken>=0.12.0",
# ]
# ///

import os
import sys
import glob
import time
import enum
import sqlite3
import hashlib
import argparse

import tiktoken
import humanfriendly

from rich.progress import Progress, MofNCompleteColumn
from rich.table import Table
from rich.console import Console

class ExitCodes(enum.IntEnum):
    OK = 0
    NOFILES = enum.auto()

TIKTOKEN_ENCODINGS = [
    "o200k_base",
    "cl100k_base",
    "p50k_base",
    "r50k_base"
]

def main():
    console = Console()

    parser = argparse.ArgumentParser(
        description="A script to wrap the tiktoken tokenizer to count tokens in a codebase.",
        epilog="Tiktoken supports several options; for more information: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb"
        )
    parser.add_argument("files", nargs="*", help="Files to scan")
    parser.add_argument("--include", action='append', default=[], help="Include files matching glob; can be specified multiple times")
    parser.add_argument("--exclude", action='append', default=[], help="Exclude files matching glob; can be specified multiple times")
    parser.add_argument("--context-window", type=int, default=0, help="The length of the content window to compare against")
    parser.add_argument("--tokenizer-encoding", choices=TIKTOKEN_ENCODINGS, default="o200k_base", help="The tokenizer encoding to use; default: o200k_base")
    parser.add_argument("--no-cache", action="store_false", dest="cache", default=True, help="Don't write to or read from the cache")

    args = parser.parse_args()

    # Expand globs
    included = set()
    for pattern in args.include:
        included.update(glob.glob(pattern, recursive=True))

    excluded = set()
    for pattern in args.exclude:
        excluded.update(glob.glob(pattern, recursive=True))

    files_accepted = list(included - excluded) + args.files
    files = sorted([f for f in files_accepted if os.path.isfile(f)])

    if not files:
        print("No files found to process. Did you specify files which don't exist?", file=sys.stderr)
        sys.exit(ExitCodes.NOFILES)

    progress = Progress(
        *Progress.get_default_columns(),
        "Files processed:",
        MofNCompleteColumn(),
        "Tokens found: {task.fields[tokens]}",
        console=console
    )

    task = progress.add_task("Tokenizing files", tokens=0, total=len(files))

    if args.cache:
        cache_conn = sqlite3.connect("cache.db")
        cur = cache_conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS cache(hash, token_count)")

        res = cur.execute("SELECT * FROM cache")
        cache_values = dict(res.fetchall())
    else:
        cache_values = dict()

    # Count tokens
    enc = tiktoken.get_encoding(args.tokenizer_encoding)
    total = 0
    files_scanned = 0
    start_time = time.monotonic()
    with progress:
        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as infile:
                    file_content = infile.read()
                    digest = hashlib.sha256(file_content.encode()).hexdigest()
                    try:
                        count = cache_values[digest]
                    except KeyError:
                        count = len(enc.encode(file_content))
                        if args.cache:
                            cur.execute("INSERT INTO cache VALUES (?, ?)", (digest, count))
                            cache_conn.commit()
                    total += count
                    progress.update(task, advance=1, tokens=humanfriendly.format_number(total))
                    files_scanned += 1
            except Exception as e:
                print(f"Skipping {path}: {e}")
    end_time = time.monotonic()

    t = Table()
    t.show_header = False
    
    t.add_row("Files scanned", humanfriendly.format_number(files_scanned))
    if args.context_window:
        tokens_used = f"{humanfriendly.format_number(total)} / {humanfriendly.format_number(args.context_window)}"
    else:
        tokens_used = f"{humanfriendly.format_number(total)}"
    t.add_row("Tokens used", tokens_used)
    if args.context_window:
        pct = round(total / args.context_window * 100)
        t.add_row("Context window used", f"{pct}%")
    t.add_row("Time taken", humanfriendly.format_timespan(end_time - start_time))
    
    console.print(t)

    # # Set outputs
    # if outfile_name := os.environ.get("GITHUB_OUTPUT",""):
    #     outfile = open(outfile_name, "a")
    # else:
    #     outfile = sys.stdout
    #     outfile.write(f"tokens={total}\n")
    #     outfile.write(f"percentage={pct}\n")
    #     outfile.write(f"badge={badge}\n")

if __name__ == '__main__':
    main()