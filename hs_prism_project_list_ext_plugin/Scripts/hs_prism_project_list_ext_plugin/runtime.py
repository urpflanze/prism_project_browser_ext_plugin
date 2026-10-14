# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

"""User-specific state and logs; independent of the plugin's install location."""

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import tempfile
import threading


LOGGER = logging.getLogger("hs_prism_project_list_ext_plugin")
LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUP_COUNT = 2
LOG_MESSAGE_MAX_BYTES = 16 * 1024
_LOG_FILE_LOCK = threading.RLock()


class _RotatingLogHandler(RotatingFileHandler):
    def shouldRollover(self, record):
        # The standard handler counts characters; UTF-8 Hungarian names/paths
        # need a byte count to keep the on-disk limit accurate as well.
        if self.stream is None:
            self.stream = self._open()
        self.stream.seek(0, os.SEEK_END)
        text = self.format(record) + self.terminator
        size = len(text.replace("\n", os.linesep).encode("utf-8"))
        return self.stream.tell() + size >= self.maxBytes

    def handleError(self, record):
        # Disk/rotation errors must not interrupt the UI or print a logging
        # traceback. The message was already sent to Prism's logging handlers.
        pass


def debug_enabled(core):
    # Both values are live: Prism can toggle debug/logging without a reload.
    return bool(getattr(core, "debugMode", False)) and LOGGER.isEnabledFor(logging.DEBUG)


def user_data_dir(core):
    # Let Prism resolve the platform default and PRISM_USER_PREFS override.
    # Keep the pre-hs_ folder so existing installations retain their settings.
    return os.path.join(core.getUserPrefDir(), "ProjectBrowserExt")


def log_message(core, message, level=logging.DEBUG):
    if level == logging.DEBUG and not debug_enabled(core):
        return
    if level < logging.WARNING and not LOGGER.isEnabledFor(level):
        return
    try:
        # Bound a single record too; a large exception must not defeat rotation.
        encoded = str(message).encode("utf-8", errors="replace")
        if len(encoded) > LOG_MESSAGE_MAX_BYTES:
            message = encoded[:LOG_MESSAGE_MAX_BYTES].decode("utf-8", errors="ignore") + " [truncated]"
        else:
            message = encoded.decode("utf-8")
        # Use Prism's configured handlers/level without changing global logging.
        LOGGER.log(level, message)
        folder = user_data_dir(core)
        os.makedirs(folder, exist_ok=True)
        # No persistent handler or core reference: unload/reload and independent
        # preference folders cannot leave duplicate handlers or open Windows files.
        with _LOG_FILE_LOCK:
            handler = _RotatingLogHandler(os.path.join(folder, "pbe_debug.log"),
                                          maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT,
                                          encoding="utf-8", delay=True)
            try:
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                record = LOGGER.makeRecord(LOGGER.name, level, __file__, 0, message, (), None)
                handler.handle(record)
            finally:
                handler.close()
    except (OSError, AttributeError, TypeError):
        # Logging must not interrupt the Project Browser.
        pass


def read_window_state(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("pos", "size"):
        values = data.get(key)
        if not isinstance(values, list) or len(values) != 2:
            return None
        if any(type(value) is not int for value in values):
            return None
    if any(value <= 0 for value in data["size"]):
        return None
    return {"pos": data["pos"], "size": data["size"]}


def write_window_state(path, data):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, delete=False) as handle:
            temporary_path = handle.name
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


class WindowStateStore:
    def __init__(self, core, legacy_path=None):
        self.path = os.path.join(user_data_dir(core), "project_list_window.json")
        # Compatibility with an existing installation from before the migration.
        self.legacy_path = legacy_path

    def read(self):
        if os.path.exists(self.path):
            return read_window_state(self.path)
        data = read_window_state(self.legacy_path) if self.legacy_path else None
        if data is not None:
            try:
                self.write(data)
            except OSError:
                # Keep the old state usable if the preference folder is read-only.
                pass
        return data

    def write(self, data):
        write_window_state(self.path, data)


DEFAULT_GRID_COLUMNS = 3
MAX_GRID_COLUMNS = 20
DEFAULT_SCROLLBAR_WIDTH = 18
MIN_SCROLLBAR_WIDTH = 10
MAX_SCROLLBAR_WIDTH = 40


class AppearancePreferencesStore:
    """Manually edited preferences, separate from automatically saved state."""

    def __init__(self, core):
        self.core = core
        self.path = os.path.join(user_data_dir(core), "appearance.json")

    def read_scrollbar_width(self):
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            try:
                write_window_state(self.path, {"scrollbar_width": DEFAULT_SCROLLBAR_WIDTH})
            except OSError as exc:
                log_message(self.core, f"[PBE] appearance defaults save failed ({self.path}): {exc}",
                            level=logging.ERROR)
            return DEFAULT_SCROLLBAR_WIDTH
        except (OSError, ValueError):
            # Never replace a user's existing file, including a malformed one.
            return DEFAULT_SCROLLBAR_WIDTH
        width = data.get("scrollbar_width", DEFAULT_SCROLLBAR_WIDTH) if isinstance(data, dict) else DEFAULT_SCROLLBAR_WIDTH
        # null explicitly requests the current Prism theme's native width.
        if width is None:
            return None
        if type(width) is not int or not MIN_SCROLLBAR_WIDTH <= width <= MAX_SCROLLBAR_WIDTH:
            return DEFAULT_SCROLLBAR_WIDTH
        return width


class GridPreferencesStore:
    def __init__(self, core):
        self.path = os.path.join(user_data_dir(core), "project_card_grid.json")

    def read_columns(self):
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return DEFAULT_GRID_COLUMNS
        columns = data.get("columns") if isinstance(data, dict) else None
        if type(columns) is not int or not 1 <= columns <= MAX_GRID_COLUMNS:
            return DEFAULT_GRID_COLUMNS
        return columns

    def write_columns(self, columns):
        if type(columns) is not int or not 1 <= columns <= MAX_GRID_COLUMNS:
            raise ValueError("Invalid grid column count")
        write_window_state(self.path, {"columns": columns})
