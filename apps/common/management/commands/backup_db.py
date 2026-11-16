import shutil
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a timestamped backup of the SQLite database in backups/"

    def handle(self, *args, **kwargs):
        db_path = Path(settings.DATABASES['default']['NAME'])
        if not db_path.exists():
            self.stderr.write(self.style.ERROR("Database file not found."))
            return

        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest_path = backup_dir / f"lifetrack_backup_{timestamp}.sqlite3"
        shutil.copy2(db_path, dest_path)

        self.stdout.write(self.style.SUCCESS(f"Backup created: {dest_path}"))