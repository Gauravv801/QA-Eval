"""
History Manager - Database CRUD operations for run history.

Migrated from JSON file storage to Supabase PostgreSQL.
Provides the same interface as before but uses database operations instead of file I/O.
"""
from typing import Optional
from utils.database_client import DatabaseClient


class HistoryManager:
    """Manages run history using Supabase database."""

    def __init__(self, registry_path='history/registry.json'):
        """
        Initialize with Supabase client.

        Args:
            registry_path: Ignored (kept for backward compatibility)
        """
        self.client = DatabaseClient.get_client()

    def load_registry(self) -> dict:
        """
        Load all runs from database (backward compatibility method).

        Returns:
            Dictionary with 'runs' list (matches old JSON structure)
        """
        runs = self.get_all_runs()
        return {"runs": runs}

    def save_registry(self, registry: dict) -> None:
        """
        No-op for backward compatibility.

        With database, we don't have a separate registry file.
        Each run is inserted individually via add_run().
        """
        pass

    def add_run(self, run_metadata: dict) -> None:
        """
        Insert a new run into database.

        Args:
            run_metadata: Dictionary with all run fields

        Raises:
            Exception: If database insert fails
        """
        try:
            response = self.client.table('runs').insert(run_metadata).execute()

            if not response.data:
                raise Exception("Insert failed - no data returned")

        except Exception as e:
            raise Exception(f"Database insert failed: {str(e)}") from e

    def get_run(self, session_id: str) -> Optional[dict]:
        """
        Retrieve run metadata by session_id.

        Args:
            session_id: UUID session identifier

        Returns:
            Run dictionary if found, None otherwise
        """
        try:
            response = self.client.table('runs')\
                .select('*')\
                .eq('session_id', session_id)\
                .execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print(f"ERROR: Failed to get run {session_id}: {e}")
            return None

    def delete_run(self, session_id: str) -> bool:
        """
        Delete run from database by session_id.

        Args:
            session_id: UUID session identifier

        Returns:
            True if run was found and deleted, False otherwise
        """
        try:
            # Check if exists first
            existing = self.get_run(session_id)
            if not existing:
                return False

            # Delete from database
            response = self.client.table('runs')\
                .delete()\
                .eq('session_id', session_id)\
                .execute()

            return True

        except Exception as e:
            print(f"ERROR: Failed to delete run {session_id}: {e}")
            return False

    def get_all_runs(self) -> list[dict]:
        """
        Get all runs sorted by saved_at descending (newest first).

        Returns:
            List of run dictionaries
        """
        try:
            response = self.client.table('runs')\
                .select('*')\
                .order('saved_at', desc=True)\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            print(f"ERROR: Failed to load runs: {e}")
            return []

    def is_session_saved(self, session_id: str) -> bool:
        """
        Check if session exists in database.

        Args:
            session_id: UUID session identifier

        Returns:
            True if session exists, False otherwise
        """
        return self.get_run(session_id) is not None
