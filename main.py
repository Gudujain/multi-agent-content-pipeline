import re
import sys
import argparse
from graph import build_graph


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]
    return slug or "output"


def main():
    parser = argparse.ArgumentParser(description="Multi-agent content pipeline")
    parser.add_argument("topic", help="Topic to write about")
    parser.add_argument("--format", choices=["blog", "thread"], default="blog")
    args = parser.parse_args()

    initial_state = {
        "topic": args.topic,
        "format": args.format,
        "research": "",
        "draft": "",
        "final": "",
        "feedback": "",
        "approved": False,
        "revision_count": 0,
        "errors": [],
    }

    app = build_graph()

    try:
        # recursion_limit = second safety belt against infinite loops
        result = app.invoke(initial_state, {"recursion_limit": 15})
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)

    path = f"output/{slugify(args.topic)}-{args.format}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(result["final"] or result["draft"])

    print(f"Saved: {path}")
    print(f"Drafts written: {result['revision_count']} | Approved: {result['approved']}")
    if result["errors"]:
        print("Warnings:")
        for err in result["errors"]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()