# Tokenator

This code was pulled from the [NanoClaw repo-tokens GitHub Action](https://github.com/qwibitai/nanoclaw/tree/main/repo-tokens) and modified for simpler purposes.

## Usage

The `--help` output is pretty comprehensive.

```
usage: tokenator.py [-h] [--include INCLUDE] [--exclude EXCLUDE] [--context-window CONTEXT_WINDOW]
                    [--tokenizer-encoding {o200k_base,cl100k_base,p50k_base,r50k_base}] [--no-cache]
                    [files ...]

A script to wrap the tiktoken tokenizer to count tokens in a codebase.

positional arguments:
  files                 Files to scan

options:
  -h, --help            show this help message and exit
  --include INCLUDE     Include files matching glob; can be specified multiple times
  --exclude EXCLUDE     Exclude files matching glob; can be specified multiple times
  --context-window CONTEXT_WINDOW
                        The length of the content window to compare against
  --tokenizer-encoding {o200k_base,cl100k_base,p50k_base,r50k_base}
                        The tokenizer encoding to use; default: o200k_base
  --no-cache            Don't write to or read from the cache

Tiktoken supports several options; for more information: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb```

TL;DR:

1. Pass `--include="<some glob>"` one or more times to list files to include
2. Pass `--exclude="<some glob>"` one or more times to list files to exclude (overrides the includes)
3. Files specified on the command line (optional) are added regardless of includes or excludes

If you specify `--context-window` the script will calculate what percentage of your context window your codebase uses.

## Encodings

You can use `--tokenizer-encoding` to specify which encoding to use; more information on these encodings is available from the OpenAI Cookbook's [How to count tokens with tiktoken](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb) document. The default is `o200k_base`, which is the tokenizer used for gpt-4o and gpt-4o-mini.

## Cache

The script keeps a cache of results in an sqlite database called `cache.db`, indexed by a sha256 hash of the file contents. If a file's hash exists in the database then the cached result will be used; otherwise, the token count will be computed as normal and stored in the DB. This allows for more rapid iterative scanning (though each file still needs its hash computed) which can be useful if you're using globs to find different 'slices' of a codebase to analyze (e.g. 'what if I do all files vs. just *.h files?').