"""Printer backend contract. Every backend (Bambuddy, simulator, future OctoPrint/Moonraker) implements
this interface; tools, the watcher and the plate-clear state machine only talk to it.

All methods are synchronous, never return raw HTTP payloads, and raise ``BackendError`` with a short,
human-readable message on failure. Write methods are only ever called from code paths that already
passed ``gates`` (see docs/DESIGN.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


class BackendError(RuntimeError):
    """A backend call failed; ``str(exc)`` is safe to show to the owner."""


# Normalised printer states (Bambuddy / Bambu MQTT ``gcode_state`` values map 1:1). ``UNKNOWN`` is a
# connected printer whose state is missing or not recognised: every gate treats it as "not idle" (fail
# closed), it is never mapped to IDLE.
IDLE, PREPARE, RUNNING, PAUSE, FINISH, FAILED, OFFLINE, UNKNOWN = (
    "IDLE", "PREPARE", "RUNNING", "PAUSE", "FINISH", "FAILED", "OFFLINE", "UNKNOWN")
ACTIVE_STATES = {PREPARE, RUNNING, PAUSE}

# Queue item statuses that will never print again (compared lower-case).
DONE_QUEUE_STATUSES = frozenset({"completed", "failed", "cancelled", "canceled", "skipped"})

# HMS codes that are known-harmless warnings and never block anything (A1 X-belt resonance notice).
IGNORED_HMS = {"0300-1000-0002-0001", "0300_1000_0002_0001"}


@dataclass
class HMSError:
    code: str  # "0500-C010-0001-0003" style
    severity: str = ""  # "fatal" | "serious" | "common" | "info" | ""
    message: str = ""
    wiki_url: str = ""

    @property
    def ignorable(self) -> bool:
        return self.code.replace("_", "-").upper() in {c.replace("_", "-").upper() for c in IGNORED_HMS}


@dataclass
class Tray:
    slot: int  # zero-based AMS tray index (what ams_mapping uses)
    material: str = ""  # "PLA", "PETG", ...
    color: str = ""  # "#RRGGBB"
    name: str = ""  # brand / preset name if known
    remain_pct: Optional[int] = None
    loaded: bool = True


@dataclass
class PrinterStatus:
    state: str  # one of the constants above
    connected: bool = True
    job_name: str = ""
    progress: float = 0.0  # 0..100
    remaining_min: Optional[int] = None
    layer: Optional[int] = None
    total_layers: Optional[int] = None
    bed_temp: Optional[float] = None
    bed_target: Optional[float] = None
    nozzle_temp: Optional[float] = None
    hms: list[HMSError] = field(default_factory=list)
    trays: list[Tray] = field(default_factory=list)
    printer_name: str = ""
    chamber_light: Optional[bool] = None  # None = the backend does not know
    awaiting_plate_clear: Optional[bool] = None  # Bambuddy waits for "plate cleared" before the next dispatch

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def blocking_hms(self) -> list[HMSError]:
        return [h for h in self.hms if not h.ignorable]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_active"] = self.is_active
        return d


@dataclass
class QueueItem:
    id: int
    status: str  # "pending" | "printing" | "completed" | "failed" | "cancelled" | "skipped"
    name: str = ""
    position: Optional[int] = None
    library_file_id: Optional[int] = None
    manual_start: bool = True
    print_time_s: Optional[int] = None
    scheduled_time: Optional[str] = None
    created_at: Optional[str] = None
    archive_id: Optional[int] = None
    # Why the printer manager gave up on the item (Bambuddy ``error_message``), e.g. a dispatch the printer
    # rejected; "" when none.
    error_message: str = ""
    # When the item really started printing (Bambuddy ``started_at``, ISO text); None = it never started. A
    # ``failed`` item without it is a start that did not happen.
    started_at: Optional[str] = None

    @property
    def is_pending(self) -> bool:
        return str(self.status or "").strip().lower() == "pending"

    @property
    def is_done(self) -> bool:
        """Finished one way or another (completed / failed / cancelled / skipped): it will not print again."""
        return str(self.status or "").strip().lower() in DONE_QUEUE_STATUSES

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModelInstance:
    profile_id: int
    title: str = ""
    printer_models: list[str] = field(default_factory=list)  # e.g. ["A1", "P1S"]
    print_time_min: Optional[int] = None
    weight_g: Optional[float] = None
    plates: Optional[int] = None
    # MakerWorld's "also compatible" printers for this instance. Their converted profiles cannot be
    # downloaded: import this instance's own profile and re-slice it with your presets.
    compatible_models: list[str] = field(default_factory=list)


@dataclass
class ModelCard:
    model_id: int
    title: str
    url: str = ""
    cover_url: str = ""
    creator: str = ""
    license: str = ""
    likes: Optional[int] = None
    downloads: Optional[int] = None
    prints: Optional[int] = None
    summary: str = ""
    instances: list[ModelInstance] = field(default_factory=list)
    already_imported_library_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LibraryFile:
    id: int
    name: str
    kind: str = ""  # "3mf" | "stl" | "gcode.3mf" | ...
    sliced: bool = False


@dataclass
class SliceOptions:
    printer_preset: str = ""  # Bambuddy local preset id (string)
    process_preset: str = ""  # process preset name or id
    filament_presets: list[str] = field(default_factory=list)  # one per filament slot
    filament_colours: list[str] = field(default_factory=list)
    bed_type: str = ""
    plate: Optional[int] = None
    process_overrides: dict = field(default_factory=dict)
    auto_orient: bool = False
    auto_arrange: bool = False


@dataclass
class SliceResult:
    library_file_id: int  # the sliced .gcode.3mf in the library
    name: str = ""
    print_time_s: Optional[int] = None
    filament_g: Optional[float] = None
    filament_types: list[str] = field(default_factory=list)
    gcode_text: str = ""  # plain G-code (may be truncated to the parts gcode.py needs)


@dataclass
class PlateCheck:
    is_empty: Optional[bool]  # None = unknown
    difference_pct: Optional[float] = None
    confidence: Optional[float] = None
    message: str = ""
    needs_calibration: bool = False
    # False = the chamber light was off for the check and could not be switched on (the result is then
    # never trusted: ``is_empty`` is None); True = the check ran lit; None = the backend does not know.
    light_ok: Optional[bool] = None
    # True when the ONLY doubt is the backend's known false-positive band (Bambuddy reads 18-25 % on an empty
    # plate): the check ran, lit and calibrated, and found a small difference. The camera alone still never
    # decides on it (``is_empty`` is None), but a person's confirmation may overrule it (``gates``).
    uncertain_band: bool = False


@dataclass
class Snapshot:
    path: Path  # local JPEG (re-encoded so messaging apps open it)
    lit: bool = True
    note: str = ""


class Backend(ABC):
    """Abstract printer backend. ``name`` is shown in tool output (``"bambuddy"`` / ``"simulator"``)."""

    name: str = "abstract"

    # True when an auto-eject print pushes the part off INSIDE its end G-code, before the printer reports FINISH
    # (the real A1 with the auto-eject preset: it waits ``M400 S900`` and sweeps the plate while the status still
    # says RUNNING at 100 %). The plate state machine then checks the plate at once at FINISH (no cool-down wait).
    # False keeps the older model: FINISH first, then cool-down and push.
    eject_in_gcode: bool = False

    # ---- read -----------------------------------------------------------------------------
    @abstractmethod
    def status(self) -> PrinterStatus: ...

    @abstractmethod
    def queue(self, include_done: bool = False) -> list[QueueItem]: ...

    @abstractmethod
    def snapshot(self, out_dir: Path, lit: bool = True) -> Snapshot:
        """Take a camera frame. For ``lit`` the chamber light is switched on when it is off and put back
        to its earlier state afterwards (a light that was on is never switched off). A light that could
        not be switched off again is reported with ``light_left_on`` in ``Snapshot.note``."""

    @abstractmethod
    def check_plate(self) -> PlateCheck:
        """Is the build plate empty? Fails closed: anything short of a lit, completed check that says
        empty gives ``is_empty`` False or None. Same light rules (and ``light_left_on`` note) as
        ``snapshot``."""

    def snapshot_and_check(self, out_dir: Path) -> tuple[Snapshot, PlateCheck]:
        """A lit photo and a plate check together. Backends with a chamber light override this to use a
        single light cycle (and so never check the plate right after switching the light off)."""
        return self.snapshot(out_dir, lit=True), self.check_plate()

    @abstractmethod
    def resolve_model(self, url_or_id: str) -> ModelCard: ...

    @abstractmethod
    def library_gcode(self, library_file_id: int, max_bytes: int = 8_000_000) -> str:
        """Plain G-code text of a sliced library file (for gates / gcode inspection)."""

    def recent_archives(self, limit: int = 5) -> list[dict]:
        return []

    def settings(self) -> dict:
        """The printer manager's own settings that matter to the workshop (Bambuddy ``GET /settings/``, e.g.
        ``require_plate_clear``); {} when the backend has none."""
        return {}

    def with_timeout(self, seconds: float) -> "Backend":
        """This backend with every request bounded to ``seconds`` (a copy where it matters; backends without
        network calls return themselves)."""
        return self

    def preview_url(self, library_file_id: int) -> str:
        return ""

    # ---- library writes (standing OK for development; still logged) ------------------------
    @abstractmethod
    def import_model(self, model_id: int, profile_id: Optional[int] = None) -> LibraryFile: ...

    @abstractmethod
    def upload_file(self, path: Path) -> LibraryFile: ...

    @abstractmethod
    def download_file(self, library_file_id: int, out_dir: Path) -> Path:
        """Download a library file (model or sliced) to ``out_dir``; returns the local path."""

    @abstractmethod
    def slice(self, library_file_id: int, options: SliceOptions, timeout_s: int = 900) -> SliceResult: ...

    # ---- queue / printer actions (always behind gates) -------------------------------------
    @abstractmethod
    def queue_add(self, library_file_id: int, *, ams_mapping: Optional[list[int]] = None,
                  plate_id: Optional[int] = None, manual_start: bool = True) -> QueueItem: ...

    @abstractmethod
    def queue_remove(self, queue_item_id: int) -> None: ...

    @abstractmethod
    def start(self, queue_item_id: int) -> QueueItem:
        """Start a pending queue item. A refusal (busy, filament missing or short, ...) raises
        ``BackendError`` with a short readable reason."""

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def pause(self) -> None: ...

    @abstractmethod
    def resume(self) -> None: ...

    @abstractmethod
    def mark_plate_cleared(self) -> None:
        """Tell the printer manager the plate is clear (Bambuddy ``POST /printers/{id}/clear-plate``)."""


def to_jsonable(obj: Any) -> Any:
    """dataclass / list / Path -> JSON-safe structure."""
    from dataclasses import is_dataclass

    if is_dataclass(obj):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, Path):
        return str(obj)
    return obj
