"""Hooks that run after operational data changes (upload commit / rollback).

Listeners register here so the upload code does not need to know about the
search index or other derived stores.
"""
import logging

logger = logging.getLogger("smart_hospital.events")

_listeners = []


def subscribe(fn):
    _listeners.append(fn)
    return fn


def data_changed(db, reason: str, batch_id=None) -> None:
    for fn in _listeners:
        try:
            fn(db, reason=reason, batch_id=batch_id)
        except Exception as exc:  # derived data must never fail the request
            logger.warning("data_changed listener %s failed: %s", getattr(fn, "__name__", fn), exc)
