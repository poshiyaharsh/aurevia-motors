"""
Django management command to safely backup the local SQLite database.
Usage:
    python manage.py backup_db
"""

import os
import sqlite3
import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Safely creates a timestamped backup of the local development database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--src',
            type=str,
            help='Source database file path (defaults to configured SQLite database)',
            default=None
        )
        parser.add_argument(
            '--dest',
            type=str,
            help='Custom directory path to store backup file',
            default=None
        )

    def handle(self, *args, **options):
        db_settings = settings.DATABASES.get('default', {})
        engine = db_settings.get('ENGINE', '')

        if 'sqlite3' not in engine:
            self.stdout.write(
                self.style.WARNING(
                    f"backup_db is optimized for SQLite. Current engine: {engine}. Skipping file-level backup."
                )
            )
            return

        raw_name = options['src'] if options['src'] else db_settings.get('NAME')

        # In-memory database detection (e.g. standard Django test runner)
        if not raw_name or ':memory:' in str(raw_name) or 'mode=memory' in str(raw_name):
            self.stdout.write(
                self.style.WARNING("In-memory SQLite database in use. File backup skipped.")
            )
            return

        db_path = Path(raw_name)
        if not db_path.exists():
            raise CommandError(f"Database file does not exist at: {db_path}")

        # Destination directory
        dest_dir = Path(options['dest']) if options['dest'] else settings.BASE_DIR / 'backups'
        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_backup_{timestamp}.sqlite3"
        backup_path = dest_dir / backup_filename

        self.stdout.write(f"Initiating safe atomic backup of {db_path.name}...")

        try:
            # Use SQLite Online Backup API for 100% atomic, consistent snapshot
            src_conn = sqlite3.connect(str(db_path))
            dest_conn = sqlite3.connect(str(backup_path))
            with dest_conn:
                src_conn.backup(dest_conn)
            dest_conn.close()
            src_conn.close()

            file_size_kb = backup_path.stat().st_size / 1024
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created backup: {backup_path.name} ({file_size_kb:.2f} KB) in {dest_dir}"
                )
            )
        except Exception as e:
            raise CommandError(f"Failed to create database backup: {e}")
