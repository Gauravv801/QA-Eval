"""
History Manager - Registry CRUD operations for run history.

Handles low-level operations for the history registry JSON file, including:
- Loading registry with corruption recovery
- Atomic writes using temp files
- Adding, retrieving, and deleting run entries
"""

import json
import shutil
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class HistoryManager:
    """Manages the history registry JSON file with atomic operations and error recovery."""

    def __init__(self, registry_path='history/registry.json'):
        """
        Initialize HistoryManager with registry path.

        Args:
            registry_path: Path to registry JSON file (default: 'history/registry.json')
        """
        self.registry_path = Path(registry_path)
        # Create directory if it doesn't exist
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load_registry(self) -> dict:
        """
        Load registry from JSON file with corruption recovery.

        Returns:
            Registry dictionary with 'runs' list.
            Returns empty structure if file doesn't exist.

        Error Handling:
            - FileNotFoundError: Returns empty registry structure
            - JSONDecodeError/ValueError: Backs up corrupt file and returns empty structure
        """
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                # Validate structure
                if 'runs' not in data:
                    raise ValueError("Invalid registry structure: missing 'runs'")
                return data
        except FileNotFoundError:
            # First time - no registry exists yet
            return {"runs": []}
        except (json.JSONDecodeError, ValueError) as e:
            # Corrupted file - backup and return fresh registry
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.registry_path}.backup.{timestamp}"

            try:
                shutil.copy2(self.registry_path, backup_path)
                print(f"WARNING: Corrupted registry backed up to {backup_path}")
                print(f"Error: {str(e)}")
            except Exception as backup_error:
                print(f"ERROR: Failed to backup corrupted registry: {backup_error}")

            # Return fresh registry
            return {"runs": []}

    def save_registry(self, registry: dict) -> None:
        """
        Atomically save registry to JSON file using temp file + rename.

        Args:
            registry: Dictionary containing 'runs' list

        Raises:
            OSError: If file operations fail
        """
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            dir=self.registry_path.parent,
            suffix='.tmp'
        ) as tmp:
            json.dump(registry, tmp, indent=2)
            tmp_path = tmp.name

        # Atomic rename (replaces existing file)
        os.replace(tmp_path, self.registry_path)

    def add_run(self, run_metadata: dict) -> None:
        """
        Add a new run to the registry.

        Args:
            run_metadata: Dictionary containing run metadata (session_id, saved_at, etc.)

        Returns:
            None
        """
        registry = self.load_registry()

        # Add to runs list
        registry['runs'].append(run_metadata)

        # Save atomically
        self.save_registry(registry)

    def get_run(self, session_id: str) -> Optional[dict]:
        """
        Retrieve run metadata by session_id.

        Args:
            session_id: UUID session identifier

        Returns:
            Run metadata dictionary if found, None otherwise
        """
        registry = self.load_registry()

        for run in registry['runs']:
            if run.get('session_id') == session_id:
                return run

        return None

    def delete_run(self, session_id: str) -> bool:
        """
        Remove run from registry by session_id.

        Args:
            session_id: UUID session identifier

        Returns:
            True if run was found and deleted, False otherwise
        """
        registry = self.load_registry()

        # Find and remove run
        initial_count = len(registry['runs'])
        registry['runs'] = [run for run in registry['runs']
                           if run.get('session_id') != session_id]

        # Check if anything was removed
        if len(registry['runs']) < initial_count:
            self.save_registry(registry)
            return True

        return False

    def get_all_runs(self) -> list[dict]:
        """
        Get all runs sorted by saved_at timestamp in descending order (newest first).

        Returns:
            List of run metadata dictionaries
        """
        registry = self.load_registry()
        runs = registry['runs']

        # Sort by saved_at descending (newest first)
        runs.sort(key=lambda r: r.get('saved_at', ''), reverse=True)

        return runs

    def is_session_saved(self, session_id: str) -> bool:
        """
        Check if session exists in registry.

        Args:
            session_id: UUID session identifier

        Returns:
            True if session is in registry, False otherwise
        """
        return self.get_run(session_id) is not None
