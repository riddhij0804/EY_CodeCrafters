"""Rebuild the ambient commerce FAISS index from current product images."""

import argparse
import os
from pathlib import Path

from index_builder import FAISSIndexBuilder


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild ambient commerce FAISS index")
    parser.add_argument("--category", default=None, help="Optional category filter")
    parser.add_argument("--subcategory", default=None, help="Optional subcategory filter")
    parser.add_argument(
        "--accuracy-mode",
        default="enhanced",
        choices=["simple", "enhanced", "ensemble"],
        help="Feature extraction accuracy mode",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if index files exist",
    )

    args = parser.parse_args()

    current_dir = Path(__file__).parent
    data_dir = (current_dir / ".." / ".." / ".." / "data").resolve()
    index_dir = current_dir / "index_cache"
    index_dir.mkdir(parents=True, exist_ok=True)

    index_path = index_dir / "products.index"
    metadata_path = index_dir / "products.metadata"

    if (index_path.exists() or metadata_path.exists()) and not args.force:
        print("Index already exists. Use --force to rebuild.")
        return 0

    if args.force:
        if index_path.exists():
            index_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

    builder = FAISSIndexBuilder(data_dir=str(data_dir), accuracy_mode=args.accuracy_mode)
    num_indexed = builder.build_index(
        category_filter=args.category,
        subcategory_filter=args.subcategory,
    )
    builder.save_index(str(index_path), str(metadata_path))

    print(f"Index built successfully with {num_indexed} products")
    print(f"Index path: {index_path}")
    print(f"Metadata path: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
