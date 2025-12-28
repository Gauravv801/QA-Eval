#!/usr/bin/env python3
"""
One-time utility to clean up orphaned session directories in outputs/.

This script identifies and deletes all session directories that are not
registered in history/registry.json.

Usage:
    python cleanup_orphaned_sessions.py [--dry-run]
"""

import argparse
import shutil
from pathlib import Path
from utils.history_manager import HistoryManager


def main():
    parser = argparse.ArgumentParser(description='Clean up orphaned session directories')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    args = parser.parse_args()

    history_manager = HistoryManager()

    print("Scanning for orphaned sessions...")

    if args.dry_run:
        print("\n[DRY RUN MODE - No files will be deleted]\n")

    # Load registry to get saved session IDs
    registry = history_manager.load_registry()
    saved_session_ids = {run['session_id'] for run in registry['runs']}

    print(f"Found {len(saved_session_ids)} saved sessions in registry")

    # Scan outputs/ directory
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        print("No outputs/ directory found - nothing to clean")
        return

    orphaned = []
    for session_dir in outputs_dir.iterdir():
        if session_dir.is_dir():
            session_id = session_dir.name
            if session_id not in saved_session_ids:
                orphaned.append((session_id, session_dir))

    print(f"Found {len(orphaned)} orphaned session directories\n")

    if not orphaned:
        print("No cleanup needed!")
        return

    # Display orphaned sessions
    print("Orphaned sessions:")
    for session_id, session_dir in orphaned:
        # Check directory size
        file_count = sum(1 for _ in session_dir.iterdir())
        print(f"  - {session_id} ({file_count} files)")

    if args.dry_run:
        print("\nRun without --dry-run to delete these directories")
        return

    # Confirm deletion
    print("\nWARNING: This will permanently delete these directories!")
    response = input("Continue? [y/N]: ")

    if response.lower() != 'y':
        print("Aborted")
        return

    # Delete orphaned sessions
    deleted_count = 0
    failed_count = 0

    for session_id, session_dir in orphaned:
        try:
            shutil.rmtree(session_dir)
            deleted_count += 1
            print(f"✓ Deleted {session_id}")
        except Exception as e:
            failed_count += 1
            print(f"✗ Failed to delete {session_id}: {e}")

    print(f"\nCleanup complete: {deleted_count} deleted, {failed_count} failed")


if __name__ == '__main__':
    main()
