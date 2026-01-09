import os
import json
from pathlib import Path

class FileManager:
    """
    Manages session-isolated file operations for the QA Evaluation Pipeline.

    Each session gets its own directory under outputs/{session_id}/ to prevent
    file conflicts in multi-user scenarios.
    """

    def __init__(self, session_id, base_location='outputs'):
        """
        Initialize FileManager with a session ID and base location.

        Args:
            session_id: Unique identifier for this session (typically a UUID)
            base_location: Root directory ('outputs' for active runs, 'history' for saved runs)
        """
        self.session_id = session_id
        self.base_location = base_location
        self.base_dir = Path(base_location).resolve() / session_id
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_path(self, filename):
        """
        Get full path for a file in this session's directory.

        Args:
            filename: Name of the file

        Returns:
            str: Absolute path to the file
        """
        return str(self.base_dir / filename)

    def save_json(self, data, filename):
        """
        Save JSON data to session directory.

        Args:
            data: Dictionary or JSON-serializable data
            filename: Name of the file to save

        Returns:
            str: Path to saved file
        """
        path = self.get_path(filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return path

    def load_json(self, filename):
        """
        Load JSON data from session directory.

        Args:
            filename: Name of the file to load

        Returns:
            dict: Parsed JSON data

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        path = self.get_path(filename)
        with open(path, 'r') as f:
            return json.load(f)

    def save_text(self, text, filename):
        """
        Save text to session directory.

        Args:
            text: Text content to save
            filename: Name of the file to save

        Returns:
            str: Path to saved file
        """
        path = self.get_path(filename)
        with open(path, 'w') as f:
            f.write(text)
        return path

    def load_text(self, filename):
        """
        Load text from session directory.

        Args:
            filename: Name of the file to load

        Returns:
            str: File contents as text

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = self.get_path(filename)
        with open(path, 'r') as f:
            return f.read()
