from django.test.runner import DiscoverRunner

from core.schema import apply_schema


class SQLTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        if self.parallel > 1:
            raise ValueError("Run SQL schema tests without --parallel.")
        databases = super().setup_databases(**kwargs)
        try:
            apply_schema()
        except Exception:
            self.teardown_databases(databases)
            raise
        return databases
