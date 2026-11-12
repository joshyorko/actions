"""An owned synthetic target with durable receipts and explicit failure points.

Only tests create this SQLite database. It represents a consumer's conditional
write contract, never Work Item/Run/Attempt state or a PostgreSQL substitute.
"""

import hashlib
import json
import sqlite3
from pathlib import Path


class OwnedEffectTarget:
    protocol = "actions.owned-synthetic-effect/v1"

    def __init__(
        self, path: Path, target_id: str, *, idempotent: bool = True, fault=None
    ):
        self.path, self.target_id, self.idempotent, self.fault = (
            path,
            target_id,
            idempotent,
            fault,
        )
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS effect (id INTEGER PRIMARY KEY,key TEXT,request TEXT,receipt TEXT)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS delivery (key TEXT,request TEXT)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS closed (key TEXT PRIMARY KEY,request TEXT,barrier TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS target (id TEXT PRIMARY KEY,idempotent INTEGER)"
            )
            existing = db.execute("SELECT id,idempotent FROM target").fetchall()
            if existing:
                assert existing == [(target_id, int(idempotent))]
            else:
                db.execute(
                    "INSERT INTO target VALUES (?,?)", (target_id, int(idempotent))
                )

    def observe(self, request):
        from actions.server.data_queries.invoice_effects import (
            EffectObservation,
            SyntheticEffectReceipt,
        )

        if self.fault == "unavailable":
            raise OSError("synthetic target unavailable")
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT request,receipt FROM effect WHERE key=?", (request.effect_key,)
            ).fetchall()
            closed = db.execute(
                "SELECT request,barrier FROM closed WHERE key=?", (request.effect_key,)
            ).fetchall()
        if closed:
            assert not rows and closed == [(request.model_dump_json(), closed[0][1])]
            return EffectObservation(state="closed_absent", barrier_id=closed[0][1])
        if not rows:
            return EffectObservation(state="absent")
        if len(rows) != 1 or json.loads(rows[0][0]) != request.model_dump(mode="json"):
            return EffectObservation(state="unknown")
        return EffectObservation(
            state="applied",
            receipt=SyntheticEffectReceipt.model_validate_json(rows[0][1]),
        )

    def apply(self, request):
        from actions.server.data_queries.invoice_effects import SyntheticEffectReceipt

        encoded = request.model_dump_json()
        fault = self.fault
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO delivery VALUES (?,?)", (request.effect_key, encoded)
            )
        if callable(fault):
            fault()
        if fault == "before_effect":
            raise OSError("synthetic pre-commit failure")
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT key FROM closed WHERE key=?", (request.effect_key,)
            ).fetchall():
                raise ValueError("synthetic effect key permanently closed")
            previous = db.execute(
                "SELECT request,receipt FROM effect WHERE key=?", (request.effect_key,)
            ).fetchall()
            if self.idempotent and previous:
                assert len(previous) == 1 and previous[0][0] == encoded
                return SyntheticEffectReceipt.model_validate_json(previous[0][1])
            receipt = SyntheticEffectReceipt(
                request=request,
                receipt_id="sha256:" + hashlib.sha256(encoded.encode()).hexdigest(),
            )
            db.execute(
                "INSERT INTO effect(key,request,receipt) VALUES (?,?,?)",
                (request.effect_key, encoded, receipt.model_dump_json()),
            )
        if fault == "lost_ack":
            raise OSError("synthetic acknowledgement lost after commit")
        if fault == "crash_after_effect":
            import os

            os._exit(24)
        return receipt

    def close(self, request):
        from actions.server.data_queries.invoice_effects import (
            EffectObservation,
            SyntheticEffectReceipt,
        )

        if not self.idempotent:
            return EffectObservation(state="unknown")
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT request,receipt FROM effect WHERE key=?", (request.effect_key,)
            ).fetchall()
            if rows:
                assert len(rows) == 1 and rows[0][0] == request.model_dump_json()
                return EffectObservation(
                    state="applied",
                    receipt=SyntheticEffectReceipt.model_validate_json(rows[0][1]),
                )
            barrier = (
                "sha256:"
                + hashlib.sha256(
                    ("closed:" + request.model_dump_json()).encode()
                ).hexdigest()
            )
            db.execute(
                "INSERT INTO closed VALUES (?,?,?) ON CONFLICT(key) DO NOTHING",
                (request.effect_key, request.model_dump_json(), barrier),
            )
        return self.observe(request)

    def counts(self):
        with sqlite3.connect(self.path) as db:
            return tuple(
                db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                for table in ("delivery", "effect")
            )
