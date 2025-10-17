# process/recategorize.py
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

# Add root directory to path to allow imports from helpers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.config import load_config
from process.evaluate import classify_content


def find_markdown_files(root_dir):
    """Finds all Markdown files in the specified root directory."""
    markdown_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    return markdown_files


def get_meta_path(md_path, root_dir):
    """Gets the corresponding .json metadata path from a .md file path."""
    # This logic assumes the structure: {root_dir}/{type}/markdown/{id}.md -> {root_dir}/{type}/metadata/{id}.json
    relative_path = os.path.relpath(md_path, start=os.path.join(root_dir))
    parts = relative_path.split(os.sep)
    if len(parts) >= 3 and parts[-2] == "markdown":
        parts[-2] = "metadata"
        # We need to reconstruct the path from the original root_dir, not just the base name
        return os.path.join(
            root_dir,
            os.path.dirname(os.path.dirname(relative_path)),
            "metadata",
            os.path.basename(md_path),
        ).replace(".md", ".json")
    return None


def calculate_hash(file_path):
    """Calculates the SHA256 hash of a file's content."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def run_recategorization(args):
    """Main logic for the recategorization script."""
    config = load_config()
    data_dir = config["data_directory"]
    all_md_files = find_markdown_files(data_dir)
    print(f"Found {len(all_md_files)} markdown files to process in '{data_dir}'.")

    for md_path in all_md_files:
        meta_path = get_meta_path(md_path, data_dir)
        if not meta_path or not os.path.exists(meta_path):
            print(f"SKIP: No metadata file found for {md_path}")
            continue

        with open(meta_path, "r") as f:
            meta = json.load(f)

        # --- Decision Logic: To process or not to process? ---
        should_process = False
        if args.rerun_all:
            should_process = True
        elif args.fix_missing and "tier_1_categories" not in meta.get("tags", []):
            # A simple check: if no Tier 1 tags, it needs processing.
            # This assumes that if we have T1 tags, we also have T2.
            should_process = True

        if not should_process:
            continue

        print(f"Processing: {md_path}")

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Get new classification
        new_classification = classify_content(content, config)

        if not new_classification:
            print("  -> Failed to classify content. Skipping update.")
            continue

        # --- Update Metadata ---
        # Clear old tags before adding new ones
        meta["tags"] = []
        meta["tags"].extend(new_classification.get("tier_1_categories", []))
        meta["tags"].extend(new_classification.get("tier_2_sub_tags", []))
        meta["category_version"] = "v1.0"  # From spec.md
        meta["last_tagged_at"] = datetime.now().isoformat()
        meta["source_hash"] = calculate_hash(md_path)

        if args.check:
            print("  -> [DRY RUN] Would update tags to:")
            print(f"     T1: {new_classification.get('tier_1_categories')}")
            print(f"     T2: {new_classification.get('tier_2_sub_tags')}")
        else:
            # Write updated metadata back to file
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)
            print("  -> Successfully updated metadata file.")


def recategorize_all_content(config):
    """
    Wrapper function to be called from other scripts like run.py.
    Forces a full recategorization of all content.
    """
    print("--- Starting Full Content Recategorization ---")

    # Mock args for the main function
    class Args:
        rerun_all = True
        fix_missing = False
        check = False

    args = Args()
    run_recategorization(args)
    print("--- Full Content Recategorization Complete ---")


def main():
    parser = argparse.ArgumentParser(
        description="Rerun categorization on existing content."
    )

    # Mode flags
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--rerun-all", action="store_true", help="Force recategorization on all files."
    )
    mode_group.add_argument(
        "--fix-missing",
        action="store_true",
        help="Only categorize files that are missing tags.",
    )

    # Behavior flags
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run. Print changes without writing to files.",
    )

    args = parser.parse_args()
    run_recategorization(args)


if __name__ == "__main__":
    main()
