"""Align migrated databases without dropping legacy output before archiving."""

from actions.server.migrations.migration_reconcile_schema import migrate as _migrate

migrate = _migrate
