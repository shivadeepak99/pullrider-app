# core/database.py
import aiosqlite
import datetime
from typing import Dict, Optional

DATABASE_URL = "pullrider.db"

async def create_tables():
    """Creates or updates the necessary database tables."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pull_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_number INTEGER NOT NULL,
                repo_full_name TEXT NOT NULL,
                title TEXT,
                author TEXT,
                created_at TIMESTAMP NOT NULL
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_number INTEGER NOT NULL,
                repo_full_name TEXT NOT NULL,
                title TEXT,
                author TEXT,
                created_at TIMESTAMP NOT NULL
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS installations (
                installation_id INTEGER PRIMARY KEY,
                gemini_api_key TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)
        await db.commit()
    print("✅ Database tables checked and ready.")

async def save_api_key(installation_id: int, api_key: str):
    """Saves or updates an API key for a given installation."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT OR REPLACE INTO installations (installation_id, gemini_api_key, created_at) VALUES (?, ?, ?)",
            (installation_id, api_key, datetime.datetime.now())
        )
        await db.commit()
    print(f"🔑 API Key saved via Easy Setup for installation_id: {installation_id}")

async def get_api_key_from_db(installation_id: int) -> Optional[str]:
    """Retrieves an API key for a given installation."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT gemini_api_key FROM installations WHERE installation_id = ?",
            (installation_id,)
        )
        row = await cursor.fetchone()
        if row:
            print(f"...API key found in database for installation {installation_id}.")
            return row[0]
        return None

async def log_pr_event(pr_number: int, repo_full_name: str, title: str, author: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO pull_requests (pr_number, repo_full_name, title, author, created_at) VALUES (?, ?, ?, ?, ?)",
            (pr_number, repo_full_name, title, author, datetime.datetime.now()))
        await db.commit()
    print(f"💾 Logged new PR #{pr_number} to the database.")

async def log_issue_event(issue_number: int, repo_full_name: str, title: str, author: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO issues (issue_number, repo_full_name, title, author, created_at) VALUES (?, ?, ?, ?, ?)",
            (issue_number, repo_full_name, title, author, datetime.datetime.now()))
        await db.commit()
    print(f"💾 Logged new Issue #{issue_number} to the database.")

async def get_dashboard_stats() -> Dict:
    """Retrieves aggregated stats from the database."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row

        pr_cursor = await db.execute("SELECT COUNT(*) as count, MAX(title) as last_title FROM pull_requests")
        pr_stats = await pr_cursor.fetchone()

        issue_cursor = await db.execute("SELECT COUNT(*) as count, MAX(title) as last_title FROM issues")
        issue_stats = await issue_cursor.fetchone()

    # THE POLISH IS HERE: This logic is now "bulletproof" against empty tables.
    # It checks not just if the row exists, but if the values inside are not None.
    return {
        "total_prs_opened": pr_stats['count'] if pr_stats and pr_stats['count'] is not None else 0,
        "total_issues_opened": issue_stats['count'] if issue_stats and issue_stats['count'] is not None else 0,
        "last_pr_title": pr_stats['last_title'] if pr_stats and pr_stats['last_title'] else "N/A",
        "last_issue_title": issue_stats['last_title'] if issue_stats and issue_stats['last_title'] else "N/A",
        "repo_health_status": "Healthy"
    }
