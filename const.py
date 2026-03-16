"""Constants for the canvas integration."""

from datetime import timedelta
from pathlib import Path
import json
from typing import Final

MANIFEST_PATH = Path(__file__).parent / "manifest.json"
with open(MANIFEST_PATH, encoding="utf-8") as f:
    INTEGRATION_VERSION: Final[str] = json.load(f).get("version", "0.0.0")

NAME = "Canvas"
DOMAIN = "canvas"
VERSION = 1
URL_BASE: Final[str] = "/canvas"

JSMODULES: Final[list[dict[str, str]]] = [
    {
        "name": "Canvas Homework Card",
        "filename": "custom-canvas-homework-card.js",
        "version": INTEGRATION_VERSION,
    },
]

HA_SENSOR = ["sensor"]

SCAN_INT = timedelta(minutes=10)

CONF_BASEURI = "baseuri"
CONF_SECRET = "token"
CONF_SEMAPHORE = "semaphore"
CONF_DISABLE_PERSISTENCE = "disable_persistence"
DEFAULT_SEMAPHORE = 15
DEFAULT_DISABLE_PERSISTENCE = False

STUDENTS = "Student(s)"
COURSES = "Course(s)"
ASSIGNMENTS = "Assignment(s)"

ATTR_STUDENTS = "_students"
ATTR_COURSES = "_courses"
ATTR_ASSIGNMENTS = "_assignments"
