"""Shared LangGraph plumbing: a process-wide SqliteSaver so interrupted runs
(human-in-the-loop approvals) survive API restarts and can be resumed from any
device."""
import sqlite3
import threading

from langgraph.checkpoint.sqlite import SqliteSaver

from ...config import settings

_lock = threading.Lock()
_saver: SqliteSaver | None = None


def checkpointer() -> SqliteSaver:
    global _saver
    with _lock:
        if _saver is None:
            conn = sqlite3.connect(str(settings.checkpoint_db), check_same_thread=False)
            _saver = SqliteSaver(conn)
        return _saver
