import json
import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path

from base import DATA_DIR, load_blog, list_blogs


class PDFGenerator:
    def __init__(self, name: str):
        self.name = name
        self.base_dir = DATA_DIR / self.name
        self.clusters_path = self.base_dir / "clusters.json"
        self.md_dir = self.base_dir / "md"
        self.out_dir = Path(__file__).parent.parent / "out"
        self.out_md = self.out_dir / f"{self.name}.md"
        self.out_pdf = self.out_dir / f"{self.name}.pdf"

    def generate(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)

        if not self.clusters_path.exists():
            print(f"[{self.name}] No clusters found.")
            return

        clusters = json.loads(self.clusters_path.read_text())
        print(
            f"[{self.name}] Generating combined markdown for {len(clusters)} chapters..."
        )

        metadata = load_blog(self.name).METADATA
        title = metadata.get("title", f"{self.name.replace('-', ' ').title()} Essays")
        author = metadata.get("author", "Unknown Author")
        cover_image_url = metadata.get("cover_image")
        flat_chapters = bool(metadata.get("flat_chapters", False))
        reverse_chronological = bool(metadata.get("reverse_chronological", False))

        cover_image_path = ""
        if cover_image_url:
            import shutil

            project_root = Path(__file__).parent.parent.resolve()
            local_candidate = project_root / cover_image_url

            if local_candidate.exists():
                actual_ext = local_candidate.suffix.lstrip(".") or "jpg"
                cover_image_path = self.out_dir / f"cover.{actual_ext}"
                shutil.copy2(local_candidate, cover_image_path)
            else:
                import urllib.request

                suffix = Path(cover_image_url).suffix.lstrip(".") or "jpg"
                cover_image_path = self.out_dir / f"cover.{suffix}"
                print(f"[{self.name}] Downloading cover image...")
                urllib.request.urlretrieve(cover_image_url, cover_image_path)

        combined_md = []
        combined_md.append("---\n")
        combined_md.append("---\n\n")

        # Create the cover page as a separate typst file to include before the body (and TOC)
        cover_typst = []
        cover_typst.append("#set page(numbering: none)\n")
        cover_typst.append('#set text(font: "Libertinus Serif", ligatures: true)\n')
        cover_typst.append("#align(center + horizon)[\n")
        cover_typst.append("  #rect(stroke: 1.5pt + black, inset: 8em, width: 100%)[\n")
        cover_typst.append("    #align(center)[\n")
        cover_typst.append(f"      #text(3.8em)[{author}]\n")

        if cover_image_path:
            cover_typst.append(
                f'      #image("/out/{cover_image_path.name}", width: 100%)\n'
            )

        cover_typst.append("      #v(0.8em)\n")
        title_parts = [p.strip() for p in str(title).splitlines() if p.strip()]
        if len(title_parts) <= 1:
            title_typst = title_parts[0] if title_parts else ""
        else:
            # Force a real line break in Typst.
            title_typst = "#linebreak()".join(title_parts)
        cover_typst.append(f'      #text(2.2em, weight: "extralight")[{title_typst}]\n')
        cover_typst.append("    ]\n")
        cover_typst.append("  ]\n")
        cover_typst.append("]\n")
        cover_typst.append("#pagebreak()\n")
        cover_typst.append('#set page(numbering: "1")\n')
        cover_typst.append("#counter(page).update(1)\n")

        cover_typst_path = self.out_dir / f"{self.name}_cover.typst"
        cover_typst_path.write_text("".join(cover_typst))

        def parse_date(lines):
            # Find the first plausible dateline (skip title, blanks, image-only lines).
            # MR uses "March 2014 · Author"; we parse only the date part before " · ".
            for line in lines[1:25]:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("[") and "](" in s and s.rstrip().endswith(")"):
                    continue
                if " · " in s:
                    s = s.split(" · ", 1)[0].strip()
                for fmt in ("%B %Y", "%Y"):
                    try:
                        return datetime.strptime(s, fmt)
                    except ValueError:
                        pass
            return datetime.min

        # Add heading style for chapters
        combined_md.append("```{=typst}\n")
        combined_md.append('#set image(height: 9cm, fit: "contain")\n')
        # Pandoc renders markdown images as `#box(image(...))`; unwrap the box so
        # our `#show image` rule can reliably turn images into centered blocks.
        combined_md.append("#show box: it => it.body\n")
        # Pandoc wraps images in inline boxes; put images in a centered block.
        combined_md.append("#show image: it => block(width: 100%)[\n")
        combined_md.append("  #align(center)[#it]\n")
        combined_md.append("]\n")
        combined_md.append("#show heading.where(level: 1): it => [\n")
        combined_md.append("  #set align(center)\n")
        combined_md.append("  #v(1em)\n")
        combined_md.append("  #line(length: 100%, stroke: 0.5pt)\n")
        combined_md.append("  #v(0.5em)\n")
        combined_md.append("  #it\n")
        combined_md.append("  #v(0.5em)\n")
        combined_md.append("  #line(length: 100%, stroke: 0.5pt)\n")
        combined_md.append("  #v(1.5em)\n")
        combined_md.append("]\n")
        combined_md.append("```\n\n")

        dotbreak_typst = (
            "```{=typst}\n"
            "#v(0.9em)\n"
            "#block(width: 100%)[#align(center)[#text(size: 1.25em, tracking: 0.35em)[...]]]\n"
            "#v(0.9em)\n"
            "```\n"
        )

        if flat_chapters:
            seen_slugs = set()
            slugs = []
            for cluster in clusters:
                for slug in cluster.get("slugs", []):
                    if slug not in seen_slugs:
                        seen_slugs.add(slug)
                        slugs.append(slug)

            essays_data = []
            manifest_path = self.base_dir / "manifest.json"
            manifest_order = {}
            if manifest_path.exists():
                manifest_order = {
                    slug: i
                    for i, slug in enumerate(
                        json.loads(manifest_path.read_text()).keys()
                    )
                }
            for slug in slugs:
                md_file = self.md_dir / f"{slug}.md"
                if md_file.exists():
                    content = md_file.read_text()
                    lines = content.split("\n")
                    dt = parse_date(lines)
                    essays_data.append(
                        {
                            "slug": slug,
                            "date": dt,
                            "order": manifest_order.get(slug, len(manifest_order)),
                            "content": content,
                        }
                    )
                else:
                    print(f"[{self.name}] Warning: {md_file} not found.")

            if reverse_chronological:
                essays_data.sort(key=lambda x: (-x["date"].toordinal(), x["order"]))
            else:
                essays_data.sort(key=lambda x: (x["date"], x["order"]))

            essay_texts = []
            for item in essays_data:
                # Keep flat books chapterless, but render article titles the
                # same way they appeared under chapter headings.
                shifted_content = re.sub(
                    r"^(#+)\s", r"#\1 ", item["content"], flags=re.MULTILINE
                )
                shifted_content = shifted_content.replace(
                    "{{DOT_BREAK}}", dotbreak_typst
                )
                essay_texts.append(shifted_content)

            combined_md.append("\n\n---\n\n".join(essay_texts))
            combined_md.append("\n\n")
        else:
            for cluster in clusters:
                chapter_name = cluster.get("chapter", "Unknown Chapter")
                slugs = cluster.get("slugs", [])

                combined_md.append(f"# {chapter_name}\n\n")

                # Read files and get dates
                essays_data = []
                for slug in slugs:
                    md_file = self.md_dir / f"{slug}.md"
                    if md_file.exists():
                        content = md_file.read_text()
                        lines = content.split("\n")
                        dt = parse_date(lines)
                        essays_data.append(
                            {"slug": slug, "date": dt, "content": content}
                        )
                    else:
                        print(f"[{self.name}] Warning: {md_file} not found.")

                # Sort chronologically (oldest first)
                essays_data.sort(key=lambda x: x["date"])

                essay_texts = []
                for item in essays_data:
                    # Shift headings by one level: # Title -> ## Title
                    shifted_content = re.sub(
                        r"^(#+)\s", r"#\1 ", item["content"], flags=re.MULTILINE
                    )
                    shifted_content = shifted_content.replace(
                        "{{DOT_BREAK}}", dotbreak_typst
                    )
                    essay_texts.append(shifted_content)

                # Join with hlines, so no hline at the end
                combined_md.append("\n\n---\n\n".join(essay_texts))
                combined_md.append("\n\n")

        self.out_md.write_text("".join(combined_md))
        print(f"[{self.name}] Combined markdown written to {self.out_md}")

        project_root = Path(__file__).parent.parent.resolve()

        print(f"[{self.name}] Converting to PDF using pandoc...")
        media_dir = self.out_dir / f"{self.name}_media"
        cmd = [
            "pandoc",
            str(self.out_md),
            "-o",
            str(self.out_pdf),
            "--pdf-engine=typst",
            f"--pdf-engine-opt=--root={project_root}",
            f"--extract-media={media_dir}",
            "--toc",
            "--toc-depth=2",
            f"--include-before-body={cover_typst_path}",
        ]

        try:
            subprocess.run(cmd, check=True)
            print(f"[{self.name}] PDF successfully generated at {self.out_pdf}")
        except subprocess.CalledProcessError as e:
            print(f"[{self.name}] Error running pandoc: {e}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else list_blogs()[0]
    PDFGenerator(name).generate()
