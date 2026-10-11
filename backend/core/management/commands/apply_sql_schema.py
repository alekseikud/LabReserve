from django.core.management.base import BaseCommand, CommandError

from core.schema import apply_schema, pending_schema_files


class Command(BaseCommand):
    help = "Apply pending SQL schema files, or check whether any are pending."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true")

    def handle(self, *args, **options):
        if options["check"]:
            pending = pending_schema_files()
            if pending:
                raise CommandError("Pending SQL files: " + ", ".join(file.name for file in pending))
            self.stdout.write("SQL schema is up to date.")
        else:
            applied = apply_schema()
            self.stdout.write("Applied: " + ", ".join(applied) if applied else "No pending SQL files.")
