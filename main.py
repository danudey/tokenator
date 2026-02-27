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
import enum
import glob
import time
import hashlib
import sqlite3
import argparse
import threading
import concurrent.futures

import tiktoken
import humanfriendly
from rich.table import Table
from rich.console import Console
from rich.progress import Progress, MofNCompleteColumn
from rich_argparse import RichHelpFormatter

try:
    CORE_COUNT = os.process_cpu_count()  # type: ignore
except AttributeError:
    CORE_COUNT = len(os.sched_getaffinity(0))


class ExitCodes(enum.IntEnum):
    OK = 0
    NOFILES = enum.auto()


TIKTOKEN_ENCODINGS = ["o200k_base", "cl100k_base", "p50k_base", "r50k_base"]

HELP_EPILOGUE = """
The tiktoken library, which this script uses, supports several encoding options; for more information about them: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
"""


class FileTokenizer:
    def __init__(self, encoding: str, cache=True):
        self.cache_data = {}
        self.cache = cache
        self.load_cache()
        self.encoding = tiktoken.get_encoding(encoding)
        self.lock = threading.Lock()

    def load_cache(self):
        if self.cache is False:
            return
        self.conn = sqlite3.connect("cache.db", check_same_thread=False)
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS cache(hash, token_count)")
        self.cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS hashdex ON cache(hash)")
        self.conn.commit()
        res = self.cur.execute("SELECT * FROM cache")
        self.cache_data = dict(res.fetchall())

    def cache_save(self, digest: str, count: int):
        with self.lock:
            try:
                self.cur.execute("INSERT INTO cache VALUES (?, ?)", (digest, count))
                self.conn.commit()
            except sqlite3.IntegrityError:
                pass
            self.cache_data[digest] = count

    def tokenize_file(self, path: str):
        with open(path, "r", encoding="utf-8", errors="ignore") as infile:
            file_content = infile.read()
            if len(file_content) == 0:
                return 0
        digest = hashlib.sha256(file_content.encode()).hexdigest()
        try:
            count = self.cache_data[digest]
        except KeyError:
            count = len(self.encoding.encode(file_content))
            self.cache_save(digest, count)
        return count


def main():
    console = Console()

    parser = argparse.ArgumentParser(
        description="A script to wrap the tiktoken tokenizer to count tokens in a codebase.",
        epilog=HELP_EPILOGUE,
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="Files to scan")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude files matching glob; can be specified multiple times",
    )
    parser.add_argument(
        "--context-window",
        type=int,
        default=0,
        help="The length of the content window to compare against",
    )
    parser.add_argument(
        "--tokenizer-encoding",
        choices=TIKTOKEN_ENCODINGS,
        default="o200k_base",
        help="The tokenizer encoding to use; default: o200k_base",
    )
    parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="cache",
        default=True,
        help="Don't write to or read from the cache",
    )
    parser.add_argument(
        "--parallel",
        default=CORE_COUNT,
        help="The number of parallel threads to use; defaults to the number of CPU cores available to the script.",
    )

    args = parser.parse_args()

    # Expand globs
    included = set()
    if args.files:
        for pattern in args.files:
            included.update(glob.glob(pattern, recursive=True))
    else:
        print("No files specified, scanning everything", file=sys.stderr)
        included.update(glob.glob("**/*", recursive=True))

    excluded = set()
    for pattern in args.exclude:
        excluded.update(glob.glob(pattern, recursive=True))

    files_accepted = list(included - excluded) + args.files
    files = sorted([f for f in files_accepted if os.path.isfile(f)])

    if not files:
        print(
            "No files specified to scan (or everything was excluded). ",
            file=sys.stderr,
        )
        sys.exit(ExitCodes.NOFILES)

    progress = Progress(
        *Progress.get_default_columns(),
        "Files processed:",
        MofNCompleteColumn(),
        "Tokens found: {task.fields[tokens]}",
        console=console,
    )

    tokenizer = FileTokenizer(args.tokenizer_encoding)

    task = progress.add_task("Tokenizing files", tokens=0, total=len(files))

    total = 0
    files_scanned = 0
    start_time = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        future_to_file = {
            executor.submit(tokenizer.tokenize_file, path): path for path in files
        }
        with progress:
            try:
                for future in concurrent.futures.as_completed(future_to_file):
                    try:
                        count = future.result()
                        total += count
                        files_scanned += 1
                        progress.update(
                            task, advance=1, tokens=humanfriendly.format_number(total)
                        )
                    except Exception as e:
                        print(f"Whoops exception: {e}")
                        raise
            except KeyboardInterrupt:
                executor.shutdown(wait=False, cancel_futures=True)
                sys.exit()

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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
