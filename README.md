# Tokenator

This code was pulled from the [NanoClaw repo-tokens GitHub Action](https://github.com/qwibitai/nanoclaw/tree/main/repo-tokens) and modified for simpler purposes.

## Installation

Use [`uv`](https://docs.astral.sh/uv/getting-started/installation/) or [`pipx`](https://pipx.pypa.io/latest/installation/):

```sh
uv tool install git+https://github.com/danudey/tokenator
```

or

```sh
pipx install git+https://github.com/danudey/tokenator
```

## Usage

The `--help` output is pretty comprehensive.

```
usage: tokenator [-h] [--include INCLUDE] [--exclude EXCLUDE] [--context-window CONTEXT_WINDOW]
                 [--tokenizer-encoding {o200k_base,cl100k_base,p50k_base,r50k_base}] [--no-cache] [--parallel PARALLEL]
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
  --parallel PARALLEL   The number of parallel threads to use; defaults to the number of CPU cores available to the script.

Tiktoken supports several options; for more information: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb```

TL;DR:

1. Pass a list of files or globs on the command-line
2. Pass `--exclude="<some glob>"` one or more times to exclude specific files or globs

Note: if you do this, the shell will expand the glob and pass the list to the script, which may result in too long of a command-line:

```sh
tokenator **/*.go
```

If you do this, the script will expand the glob itself:

```sh
tokenator '**/*.go'
```

Do with this information what you will.

## Context

If you specify `--context-window` the script will calculate what percentage of your context window your codebase uses. No other effect.

## Encodings

You can use `--tokenizer-encoding` to specify which encoding to use; more information on these encodings is available from the OpenAI Cookbook's [How to count tokens with tiktoken](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb) document. The default is `o200k_base`, which is the tokenizer used for gpt-4o and gpt-4o-mini.

Note that different AIs and AI generations tokenize differently, so Opus 4.6 may have a significantly different token count. If there are ways to add different tokenizers to tiktoken, let me know. PRs to use other tokenizers are also welcome!

## Cache

The script keeps a cache of results in an sqlite database called `cache.db`, indexed by a sha256 hash of the file contents. If a file's hash exists in the database then the cached result will be used; otherwise, the token count will be computed as normal and stored in the DB. This allows for more rapid iterative scanning (though each file still needs its hash computed) which can be useful if you're using globs to find different 'slices' of a codebase to analyze (e.g. 'what if I do all files vs. just *.h files?').

## Parallel

By default the script will run multiple threads in parallel; the number of threads defaults to the number of CPU cores currently available to the process (which may not be the same as the number of CPU cores on the system). See https://docs.python.org/3/library/os.html#os.process_cpu_count for implementation details. You can override the default with `--parallel`.