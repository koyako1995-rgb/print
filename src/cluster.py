"""Assign knapsack-chosen essays to chapters."""

import json
import sys

from base import DATA_DIR, load_blog, list_blogs


class ClusterSolver:
    def __init__(self, name: str, topics: dict[str, list[str]]):
        self.name = name
        self.topics = topics
        self.base_dir = DATA_DIR / self.name
        self.knapsack_path = self.base_dir / "knapsack.json"
        self.cache_path = self.base_dir / "clusters.json"

    def cluster(self):
        if not self.knapsack_path.exists():
            print(f"[{self.name}] No knapsack output found. Run knapsack.py first.")
            return

        chosen_slugs = json.loads(self.knapsack_path.read_text()).get(
            "chosen_slugs", []
        )
        print(f"[{self.name}] Clustering {len(chosen_slugs)} chosen essays...")

        slug_to_topic = {
            slug: topic for topic, slugs in self.topics.items() for slug in slugs
        }

        clusters: dict[str, list[str]] = {topic: [] for topic in self.topics}
        clusters["Other"] = []
        for slug in chosen_slugs:
            clusters[slug_to_topic.get(slug, "Other")].append(slug)

        final_clusters = [
            {"chapter": topic, "slugs": slugs}
            for topic, slugs in clusters.items()
            if slugs
        ]

        self.cache_path.write_text(json.dumps(final_clusters, indent=2))
        print(f"[{self.name}] Clustered into {len(final_clusters)} topics.")
        for cluster in final_clusters:
            print(f"  - {cluster['chapter']}: {len(cluster['slugs'])} essays")
        return final_clusters


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else list_blogs()[0]
    ClusterSolver(name, load_blog(name).TOPICS).cluster()
