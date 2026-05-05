"""Score and rank cached essays using Google Search API."""

import sys
from base import load_blog, list_blogs

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else list_blogs()[0]
    load_blog(name).Scorer().score_all()
