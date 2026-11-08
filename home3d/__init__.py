"""home-3d-workshop core package.

Layout (see docs/DESIGN.md):
  config      Settings + data dir resolution (works inside and outside Hermes)
  backends    Printer backends: ``bambuddy`` (real) and ``simulator`` (no hardware)
  store       SQLite household memory, jobs, events, human-needed moments, upgrades
  gcode       Sliced-file inspection (eject marker, temps, footprint, time, grams)
  gates       Pure safety decisions (start / eject / clear-plate)
  eject       Plate-clear state machine
  messages    Owner vs family message templates (tr / en)
  notify      Zero-token delivery through ``hermes send``
  watcher     Zero-token event watcher (cron --no-agent script entry point)
  upgrades    Human-needed moments -> upgrade proposals
  customize   Pure-python model scaling + optional OpenSCAD templates
  tools / hooks / commands / cli / plugin   Hermes surfaces
"""

PLUGIN_NAME = "home-3d-workshop"
TOOLSET = "home_3d_workshop"
__version__ = "0.1.0"
