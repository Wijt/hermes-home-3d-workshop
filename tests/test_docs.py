"""The docs stay true to the code: subtitle reading speed, the demo picture, and the numbers the README quotes."""

from __future__ import annotations

import re
import xml.dom.minidom
from pathlib import Path

from home3d_ws.home3d import cli, eject, hooks, watcher
from home3d_ws.home3d.backends import simulator

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _srt(path: Path) -> list[tuple[float, float, str]]:
    def secs(t: str) -> float:
        h, m, rest = t.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        lines = block.splitlines()
        a, b = (secs(x.strip()) for x in lines[1].split("-->"))
        cues.append((a, b, "\n".join(lines[2:])))
    return cues


def test_subtitles_are_readable_and_end_in_time():
    # docs/DEMO.md: every cue at 17 characters per second or slower (line break counted), no overlaps,
    # at most 2 lines of 42 characters, cues end by 1:25.0
    for name in ("subtitles.en.srt", "subtitles.tr.srt"):
        cues = _srt(ROOT / "docs" / "demo" / name)
        assert cues, name
        prev_end = -1.0
        for a, b, text in cues:
            assert b - a >= 1.0, (name, text)
            assert len(text) / (b - a) <= 17.0, (name, text, round(len(text) / (b - a), 1))
            assert a >= prev_end, (name, "overlap", text)
            lines = text.split("\n")
            assert len(lines) <= 2 and max(len(x) for x in lines) <= 42, (name, text)
            prev_end = b
        assert cues[-1][1] <= 85.0, name


def test_demo_picture_is_valid_svg_without_private_paths():
    svg = (ROOT / "docs" / "demo-terminal.svg").read_text(encoding="utf-8")
    xml.dom.minidom.parseString(svg.encode("utf-8"))
    assert "hermes home3d demo" in svg
    assert not re.search(r"/home/|/tmp/|/Users/", svg)
    assert not re.search(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b",
                         svg)
    assert "demo-terminal.svg" in README


def test_cli_offers_every_simulator_scenario():
    assert set(cli.SCENARIOS) == set(simulator.SCENARIOS)
    listed = re.search(r"simulate scenario (\w+)\s+# also: ([\w, ]+)", README)
    assert listed is not None
    assert {listed.group(1)} | {s.strip() for s in listed.group(2).split(",")} == set(simulator.SCENARIOS)


def test_readme_quotes_the_real_hook_and_light_limits():
    # README, docs/catalog and docs/DESIGN.md quote these numbers: change them together
    assert hooks.HOOK_REQUEST_TIMEOUT_S == 5 and hooks.HOOK_DEADLINE_S == 12
    assert "at most 5 seconds per" in README and "12 seconds in all" in README
    assert [s // 60 for s in watcher.RECHECK_BACKOFF_S] == [15, 30, 60, 120] and watcher.MAX_RECHECKS == 6
    assert "15, 30, 60, then 120 minutes, at most 6 times" in README
    assert eject.EJECT_RECHECK_S == 3 * 60
