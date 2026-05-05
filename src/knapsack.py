import json
import sys
import time

from base import DATA_DIR, list_blogs


class KnapsackSolver:
    def __init__(self, name: str, max_words: int = 75000):
        self.name = name
        self.max_words = max_words
        self.base_dir = DATA_DIR / self.name
        self.manifest_path = self.base_dir / "manifest.json"
        self.cache_path = self.base_dir / "knapsack.json"

    def solve(self):
        if self.cache_path.exists():
            print(f"[{self.name}] Loading cached knapsack result...")
            result = json.loads(self.cache_path.read_text())
            print(
                f"[{self.name}] Knapsack solved (cached). Chose {len(result['chosen_slugs'])} essays, total words: {result['total_words']}, total score: {result['total_score']:.3f}"
            )
            return result

        if not self.manifest_path.exists():
            print(f"[{self.name}] No manifest found.")
            return

        manifest = json.loads(self.manifest_path.read_text())

        items = []
        for slug, meta in manifest.items():
            words = meta.get("words", 0)
            score = meta.get("score", 0.0)
            if words > 0:
                items.append(
                    {
                        "slug": slug,
                        "words": words,
                        "score": score,
                        "title": meta.get("title", slug),
                    }
                )

        print(
            f"[{self.name}] Solving knapsack for {len(items)} items, max_words={self.max_words}..."
        )
        start_time = time.time()

        n = len(items)
        W = self.max_words

        # dp[w] stores (score, words_used)
        dp = [(0.0, 0)] * (W + 1)
        choices = [bytearray(W + 1) for _ in range(n)]

        for i, item in enumerate(items):
            weight = item["words"]
            # Add a tiny value proportional to weight so that if scores are equal, we prefer to fill the capacity.
            # But the user only said "score".
            # We'll just use the score. To maximize word count when score is 0, we can use a tuple.
            value = item["score"]
            for w in range(W, weight - 1, -1):
                prev_score, prev_words = dp[w - weight]
                new_score = prev_score + value
                new_words = prev_words + weight

                curr_score, curr_words = dp[w]

                # We want to maximize score first. If scores are extremely close, maximize words.
                if new_score - curr_score > 1e-9 or (
                    abs(new_score - curr_score) <= 1e-9 and new_words > curr_words
                ):
                    dp[w] = (new_score, new_words)
                    choices[i][w] = 1

        chosen_slugs = []
        w = W
        for i in range(n - 1, -1, -1):
            if choices[i][w]:
                chosen_slugs.append(items[i]["slug"])
                w -= items[i]["words"]

        chosen_slugs.reverse()

        final_score = dp[W][0]
        final_words = dp[W][1]

        result = {
            "max_words": self.max_words,
            "total_words": final_words,
            "total_score": final_score,
            "chosen_slugs": chosen_slugs,
        }

        self.cache_path.write_text(json.dumps(result, indent=2))

        elapsed = time.time() - start_time
        print(
            f"[{self.name}] Knapsack solved in {elapsed:.2f}s. Chose {len(chosen_slugs)} essays, total words: {result['total_words']}, total score: {result['total_score']:.3f}"
        )
        return result


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else list_blogs()[0]
    KnapsackSolver(name).solve()
