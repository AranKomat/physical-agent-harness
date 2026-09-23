"""Episode-local append-only memory. No dependency on WorldState or TaskLedger."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Callable

from physical_harness.world.memory.schemas import (
    Asset,
    Card,
    Cutoff,
    Draft,
    encoded,
    finite,
    from_payload,
    integer,
    payload,
    text,
)


class MemoryStore:
    """One database per episode. Each append gets a durable knowledge watermark.

    This is a ten-minute-episode reference store, not a distributed vector DB.
    All writes are short locked transactions. Model inference never holds this
    lock. Raw blobs remain in the existing content-addressed EvidenceStore.
    """

    def __init__(self, path: str | Path, episode_id: str, read_blob: Callable[[str], bytes]):
        self.episode_id = text(episode_id)
        self.read_blob = read_blob
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('beliefs','task_support')").fetchone():
            self.db.close()
            raise ValueError('Use a separate memory database, not WorldState')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                UNIQUE(kind,id));
            CREATE INDEX IF NOT EXISTS records_kind ON records(kind,seq);
        ''')
        try:
            with self.db:
                old = self.db.execute("SELECT value FROM meta WHERE key='episode'").fetchone()
                if old and old[0] != episode_id:
                    raise ValueError('Database belongs to another episode')
                version = self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
                if version and version[0] != '1':
                    raise ValueError('Unsupported memory schema')
                self.db.execute("INSERT OR IGNORE INTO meta VALUES('episode',?)", (episode_id,))
                self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema','1')")
        except Exception:
            self.db.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        with self._lock:
            self.db.close()

    def watermark(self) -> int:
        with self._lock:
            return self.db.execute('SELECT COALESCE(MAX(seq),0) FROM records').fetchone()[0]

    def cutoff(self, observed_through: float) -> Cutoff:
        return Cutoff(self.episode_id, observed_through, self.watermark())

    def _check_cutoff(self, cutoff: Cutoff):
        if cutoff.episode_id != self.episode_id or cutoff.knowledge_seq > self.watermark():
            raise ValueError('Foreign episode or future knowledge watermark')

    def _get(self, kind: str, identifier: str):
        row = self.db.execute('SELECT * FROM records WHERE kind=? AND id=?',
                              (kind, identifier)).fetchone()
        return (row['seq'], json.loads(row['body'])) if row else None

    def _append(self, kind: str, identifier: str, body: dict) -> tuple[int, bool]:
        data = encoded(body).decode('utf-8')
        previous = self.db.execute('SELECT seq,body FROM records WHERE kind=? AND id=?',
                                   (kind, identifier)).fetchone()
        if previous:
            if previous['body'] != data:
                raise ValueError('Conflicting reuse of immutable memory ID')
            return previous['seq'], False
        row = self.db.execute('INSERT INTO records(kind,id,body) VALUES(?,?,?)',
                              (kind, identifier, data))
        return row.lastrowid, True

    def add_asset(self, asset: Asset) -> int:
        if asset.episode_id != self.episode_id:
            raise ValueError('Foreign episode asset')
        data = self.read_blob(asset.uri)
        if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != asset.sha256:
            raise ValueError('Source artifact hash mismatch')
        with self._lock, self.db:
            if asset.kind == 'crop':
                parent = self.asset(asset.parent_id)
                if parent.kind != 'image':
                    raise ValueError('Crop must reference an original image')
                if (asset.observed_start, asset.observed_end, asset.camera, asset.observation_id) != (
                        parent.observed_start, parent.observed_end, parent.camera, parent.observation_id):
                    raise ValueError('Crop changed source capture time, camera or observation')
                if asset.crop_box[2] > parent.width or asset.crop_box[3] > parent.height:
                    raise ValueError('Crop exceeds parent image')
            return self._append('asset', asset.asset_id, payload(asset))[0]

    def asset(self, identifier: str, cutoff: Cutoff | None = None) -> Asset:
        with self._lock:
            result = self._get('asset', identifier)
            if not result:
                raise ValueError('Unknown source asset')
            seq, data = result
            asset = from_payload(Asset, data)
            if cutoff:
                self._check_cutoff(cutoff)
                if seq > cutoff.knowledge_seq or asset.observed_end > cutoff.observed_through:
                    raise ValueError('Asset unavailable at decision cutoff')
            return asset

    def read_asset(self, identifier: str, cutoff: Cutoff) -> bytes:
        asset = self.asset(identifier, cutoff)
        data = self.read_blob(asset.uri)
        if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != asset.sha256:
            raise ValueError('Source artifact hash mismatch')
        return data

    def add_card(self, card: Card) -> int:
        if card.episode_id != self.episode_id:
            raise ValueError('Foreign episode card')
        with self._lock, self.db:
            for identifier in card.asset_ids:
                asset = self.asset(identifier)
                if not card.observed_start <= asset.observed_start <= asset.observed_end <= card.observed_end:
                    raise ValueError('Card includes evidence outside event interval')
            if card.kind == 'motion' and not any(
                    self.asset(i).kind == 'clip' for i in card.asset_ids):
                images = [self.asset(i) for i in card.asset_ids
                          if self.asset(i).kind in {'image', 'crop'}]
                if len({a.observed_end for a in images}) < 2:
                    raise ValueError('Motion needs a clip or multiple temporally distinct images')
            return self._append('card', card.card_id, payload(card))[0]

    def card(self, identifier: str, cutoff: Cutoff | None = None) -> Card:
        with self._lock:
            result = self._get('card', identifier)
            if not result:
                raise ValueError('Unknown memory card')
            seq, data = result
            card = from_payload(Card, data)
            if cutoff:
                self._check_cutoff(cutoff)
                if seq > cutoff.knowledge_seq or card.observed_end > cutoff.observed_through:
                    raise ValueError('Card unavailable at decision cutoff')
                for identifier in card.asset_ids:
                    self.asset(identifier, cutoff)
            return card

    def cards(self, cutoff: Cutoff, *, max_scan: int = 5000) -> list[Card]:
        integer(max_scan, 1)
        with self._lock:
            self._check_cutoff(cutoff)
            rows = self.db.execute("SELECT body FROM records WHERE kind='card' AND seq<=? ORDER BY seq LIMIT ?",
                                   (cutoff.knowledge_seq, max_scan + 1)).fetchall()
            if len(rows) > max_scan:
                raise ValueError('Episode memory exceeds reference scan budget; add indexed retrieval')
            return [card for row in rows
                    if (card := from_payload(Card, json.loads(row[0]))).observed_end <= cutoff.observed_through]

    def add_annotation(self, card_id: str, draft: Draft, *, model: str, prompt_id: str,
                       basis: Cutoff, wall_seconds: float) -> int:
        """Only narration is stored. No method here can modify robot/task beliefs."""
        text(model)
        text(prompt_id)
        finite(wall_seconds)
        with self._lock, self.db:
            card = self.card(card_id, basis)
            if not set(draft.cited_asset_ids) <= set(card.asset_ids):
                raise ValueError('Writer cited evidence not in its input card')
            for identifier in draft.cited_asset_ids:
                self.asset(identifier, basis)
            identifier = f'{card_id}:{model}:{prompt_id}'
            body = {'card_id': card_id, 'draft': payload(draft), 'model': model,
                    'prompt_id': prompt_id, 'basis': payload(basis),
                    'wall_seconds': wall_seconds, 'authority': 'untrusted_narration'}
            return self._append('annotation', identifier, body)[0]

    def annotation(self, card_id: str, cutoff: Cutoff) -> dict | None:
        with self._lock:
            self.card(card_id, cutoff)
            rows = self.db.execute("SELECT body FROM records WHERE kind='annotation' AND seq<=? ORDER BY seq DESC",
                                   (cutoff.knowledge_seq,)).fetchall()
            for row in rows:
                body = json.loads(row[0])
                if body['card_id'] == card_id:
                    return body
            return None

    def reserve_job(self, job_id: str, body: dict, *, max_calls: int) -> str:
        """Ambiguous/crashed reservations are not retried automatically."""
        integer(max_calls, 0)
        with self._lock, self.db:
            if self._get('job', job_id):
                return 'duplicate'
            count = self.db.execute("SELECT COUNT(*) FROM records WHERE kind='job'").fetchone()[0]
            if count >= max_calls:
                return 'budget_exhausted'
            self._append('job', text(job_id), body)
            return 'reserved'

    def record_job_result(self, job_id: str, status: str, *, wall_seconds: float = 0):
        if status not in {'done', 'failed', 'queue_full', 'stopped'}:
            raise ValueError('Invalid worker result')
        finite(wall_seconds)
        with self._lock, self.db:
            if not self._get('job', job_id):
                raise ValueError('Job not reserved')
            self._append('job_result', job_id, {'status': status, 'wall_seconds': wall_seconds})

    def job_results(self) -> list[dict]:
        with self._lock:
            return [dict(id=r['id'], **json.loads(r['body'])) for r in self.db.execute(
                "SELECT id,body FROM records WHERE kind='job_result' ORDER BY seq")]
