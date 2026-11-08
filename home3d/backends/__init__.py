"""Backend factory."""

from __future__ import annotations

from ..config import Settings, get_api_key
from .base import Backend, BackendError


def make_backend(settings: Settings) -> Backend:
    if settings.backend == "bambuddy":
        if not settings.bambuddy_url:
            raise BackendError("backend is 'bambuddy' but bambuddy_url is not set")
        from .bambuddy import BambuddyBackend

        return BambuddyBackend(settings.bambuddy_url, printer_id=settings.printer_id,
                               api_key=get_api_key(), public_url=settings.link_base)
    from .simulator import SimulatorBackend

    return SimulatorBackend()


__all__ = ["Backend", "BackendError", "make_backend"]
