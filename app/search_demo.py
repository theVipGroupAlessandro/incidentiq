"""Try a semantic search from the command line.

Examples:
  python -m app.search_demo "payment cannot get a database connection" --model minilm
  python -m app.search_demo "payment errors" --logs --service payment order gateway
      --start 2026-11-09T10:00:00Z --end 2026-11-09T11:30:00Z
"""
import argparse

from app.corpus import load_corpus
from app.embeddings import MODELS, build_index
from app.logs import in_window, log_documents


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--model", choices=MODELS, default="bge-small")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--logs", action="store_true", help="search log groups instead of incidents and ADRs")
    parser.add_argument("--service", nargs="*", help="only these services")
    parser.add_argument("--start", help="logs only: window start, e.g. 2026-11-09T10:00:00Z")
    parser.add_argument("--end", help="logs only: window end")
    args = parser.parse_args()

    documents = log_documents() if args.logs else load_corpus()
    filters = []
    if args.service:
        filters.append(lambda doc: set(doc["services"]) & set(args.service))
    if args.logs and args.start and args.end:
        filters.append(in_window(args.start, args.end))

    index = build_index(documents, args.model)
    print(f"Model: {MODELS[args.model]['name']}  |  Query: {args.query}\n")
    for doc, score in index.search(args.query, top_k=args.top, where=lambda d: all(f(d) for f in filters)):
        extra = f"  x{doc['count']}  {doc['first_seen'][:19]}" if args.logs else ""
        print(f"{score:.3f}  {doc['doc_id']:<22}{extra}  {doc['text'][:80]}")


if __name__ == "__main__":
    main()