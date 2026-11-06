"""Download the corpus in data/corpus_sources.json.

Usage: uv run python scripts/fetch_corpus.py [--only DOC_ID ...]
"""

import sys

from madhya_kanoon_saathi.ingestion.fetch import main

if __name__ == "__main__":
    sys.exit(main())
