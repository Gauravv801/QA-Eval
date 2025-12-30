"""
Database Client - Supabase connection management for persistent storage.

Provides singleton access to Supabase client for database and storage operations.
Credentials loaded from Streamlit secrets (cloud) or .env (local development).
"""
from supabase import create_client, Client
import streamlit as st
import os
from typing import Optional


class DatabaseClient:
    """Singleton client for Supabase connections."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.

        Credentials loaded from (in order):
        1. Streamlit secrets (production on Streamlit Cloud)
        2. Environment variables (local development with .env)

        Returns:
            Supabase Client instance

        Raises:
            ValueError: If credentials not found in either location
        """
        if cls._instance is None:
            # Try Streamlit secrets first (cloud), fallback to .env (local)
            try:
                supabase_url = st.secrets["SUPABASE_URL"]
                supabase_key = st.secrets["SUPABASE_SERVICE_KEY"]  # Use service_role key
            except (FileNotFoundError, KeyError, AttributeError):
                # Fallback to environment variables
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError(
                    "Missing Supabase credentials. Set SUPABASE_URL and "
                    "SUPABASE_SERVICE_KEY in .streamlit/secrets.toml or .env"
                )

            cls._instance = create_client(supabase_url, supabase_key)

        return cls._instance

    @classmethod
    def reset_client(cls):
        """Reset client instance (useful for testing)."""
        cls._instance = None
