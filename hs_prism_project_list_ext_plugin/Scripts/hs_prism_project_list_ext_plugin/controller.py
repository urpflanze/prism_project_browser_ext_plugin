# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

import logging
import os

from qtpy.QtCore import QEvent, QObject, QTimer, QSize, Qt
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from .ui_widgets import CurrentProjectBanner, ProjectListSummary, ScrollbarWidthOverride
from .runtime import AppearancePreferencesStore, GridPreferencesStore, WindowStateStore, debug_enabled, log_message
from .card_grid import ProjectCardGrid
from .window_geometry import fit_window


LEGACY_WINDOW_STATE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "project_list_window.json")
)
WINDOW_STATE_DEBOUNCE_MS = 300


class ProjectBrowserController(QObject):
    def __init__(self, core, project_list_dialog, patches):
        super(ProjectBrowserController, self).__init__(project_list_dialog)
        self.core = core
        self.dialog = project_list_dialog
        self._patches = patches
        self._disposed = False
        self._container = None
        self._banner = None
        self._summary = None
        self._window_state = WindowStateStore(core, LEGACY_WINDOW_STATE_PATH)
        self._grid_preferences = GridPreferencesStore(core)
        self._appearance_preferences = AppearancePreferencesStore(core)
        self._scrollbar_appearance = ScrollbarWidthOverride(self.dialog.sa_projects)
        self._grid = ProjectCardGrid(self.dialog, self._grid_preferences.read_columns(), self)
        self._applying_size = False
        self._opening_geometry = False
        self._pending_window_save = False
        self._pending_window_state = None
        self._last_window_geometry = None
        self._banner_show_connected = False
        self._original_window_flags = self.dialog.windowFlags()
        self._original_horizontal_scroll_policy = self.dialog.sa_projects.horizontalScrollBarPolicy()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_window_state)
        self.dialog.destroyed.connect(self._on_dialog_destroyed)
        self._owner = self.dialog.parentWidget()
        if self._owner is not None:
            self._owner.destroyed.connect(self._on_owner_destroyed)
        QApplication.instance().aboutToQuit.connect(self._on_application_quit)

    def _on_owner_destroyed(self, *args):
        if self._disposed:
            return
        # The parent's destroyed signal arrives while this child dialog is
        # still usable. Flush before returning its layout to native Qt; doing
        # this after the dialog's own destroyed signal is too late.
        self._finish_window_session(capture_current=self.dialog.isVisible())
        self._release_grid_before_delete()

    def _release_grid_before_delete(self):
        was_applying = self._applying_size
        self._applying_size = True
        try:
            self._grid.dispose()
        finally:
            self._applying_size = was_applying

    def _disconnect_owner_destroyed(self):
        if self._owner is not None:
            try:
                self._owner.destroyed.disconnect(self._on_owner_destroyed)
            except (RuntimeError, TypeError):
                pass
        self._owner = None

    def _on_application_quit(self):
        if not self._disposed:
            self._finish_window_session(capture_current=self.dialog.isVisible())

    def _disconnect_application_quit(self):
        app = QApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self._on_application_quit)
            except (RuntimeError, TypeError):
                # QApplication may already be tearing down its connections.
                pass

    def _on_dialog_destroyed(self, *args):
        # The QWidget is already invalid here: only use the cached geometry.
        # Qt deletes the controller and its child timers after this signal.
        self._save_timer.stop()
        self._grid.abandon()
        self._disconnect_owner_destroyed()
        self._write_pending_window_state()
        self._disconnect_application_quit()
        self._disposed = True
        self._clear_dialog_references()
        self.dialog = None
        self._patches = None
        self._container = self._banner = self._summary = None

    def _clear_dialog_references(self):
        for name in (
            "_pbe_controller", "_pbe_container", "_pbe_banner", "_pbe_summary",
            "_pbe_hooks_installed", "_pbe_orig_move",
            "_pbe_in_show",
        ):
            self.dialog.__dict__.pop(name, None)

    def dispose(self):
        if self._disposed:
            return
        # Save before removing UI/flags, which can change the geometry.
        self._finish_window_session(capture_current=self.dialog.isVisible())
        self._disconnect_application_quit()
        self._disconnect_owner_destroyed()
        self._disposed = True
        dialog = self.dialog
        dialog.removeEventFilter(self)
        if self._banner_show_connected:
            dialog.signalShowing.disconnect(self._on_showing)
            self._banner_show_connected = False
        dialog.destroyed.disconnect(self._on_dialog_destroyed)
        self._grid.dispose()
        self._scrollbar_appearance.dispose()
        if self._container is not None:
            dialog.lo_main.removeWidget(self._container)
            self._container.hide()
            self._container.setParent(None)
            self._container.deleteLater()
        if getattr(dialog, "_pbe_showwidget_patched", False):
            dialog.setWindowFlags(self._original_window_flags)
        dialog.sa_projects.setHorizontalScrollBarPolicy(self._original_horizontal_scroll_policy)
        self._clear_dialog_references()
        self.dialog = None
        self._patches = None
        self._container = self._banner = self._summary = None
        self.setParent(None)
        self.deleteLater()

    def record_restored_geometry(self):
        # Showing a framed window can shift its Qt coordinates. This belongs
        # to restore, not a user move that should replace the saved position.
        if not self._pending_window_save:
            self._last_window_geometry = self._current_window_state()

    def _finish_window_session(self, capture_current=True):
        self._save_timer.stop()
        self._grid.stop()
        if capture_current:
            self._capture_window_state()
        self._write_pending_window_state()

    @property
    def debug(self):
        return debug_enabled(self.core)

    def _log(self, message, level=logging.DEBUG):
        log_message(self.core, message, level=level)

    def ensure_ui(self):
        if self._disposed:
            return
        # UI egyszeri letrehozasa, hogy ne duplazzon frissiteskor.
        if getattr(self.dialog, "_pbe_container", None):
            self._container = self.dialog._pbe_container
            self._banner = self.dialog._pbe_banner
            self._summary = self.dialog._pbe_summary
            self._install_dialog_hooks()
            return

        container = QWidget()
        container.setObjectName("pbe_container")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(9, 6, 9, 6)
        layout.setSpacing(6)

        banner = CurrentProjectBanner()
        summary = ProjectListSummary()
        summary.set_columns(self._grid.columns)
        summary.columnsChanged.connect(self._on_grid_columns_changed)
        layout.addWidget(banner)
        layout.addWidget(summary)

        # A keresosor es a lista koze szurjuk be, a Prism UI-t nem irjuk felul.
        self.dialog.lo_main.insertWidget(1, container)
        self.dialog.sa_projects.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.dialog._pbe_container = container
        self.dialog._pbe_banner = banner
        self.dialog._pbe_summary = summary
        self._container = container
        self._banner = banner
        self._summary = summary
        self._install_dialog_hooks()

    def refresh(self):
        if self._disposed:
            return
        # Widgetek szinkronban tartasa a Prism allapotaval.
        if not self._banner or not self._summary:
            self.ensure_ui()

        self.refresh_current_project()

        projects = getattr(self.dialog, "projects", []) or []
        filter_text = ""
        if hasattr(self.dialog, "e_search"):
            filter_text = self.dialog.e_search.text()
        self._summary.set_summary(len(projects), filter_text)
        self._resize_project_cards()

    def refresh_current_project(self):
        if self._disposed:
            return
        if self._banner is None:
            self.ensure_ui()
        project_name = getattr(self.core, "projectName", "") or "No active project"
        project_path = getattr(self.core, "projectPath", "") or ""
        self._banner.set_project(project_name, project_path)

    def _install_dialog_hooks(self):
        if getattr(self.dialog, "_pbe_hooks_installed", False):
            return

        if hasattr(self.dialog, "signalShowing"):
            self.dialog.signalShowing.connect(self._on_showing)
            self._banner_show_connected = True
        self.dialog.installEventFilter(self)
        self.dialog._pbe_hooks_installed = True

    def _on_showing(self):
        self._scrollbar_appearance.set_width(self._appearance_preferences.read_scrollbar_width())
        self.refresh_current_project()
        if getattr(self.dialog, "_pbe_in_show", False):
            if not self.apply_saved_dialog_state():
                self.fit_dialog_to_screen()
        elif not getattr(self.dialog, "_pbe_showwidget_patched", False):
            self._apply_saved_dialog_pos()
        # Native Show/Move before this signal belongs to restore. Input in
        # Prism's following processEvents must already be allowed to save.
        self._opening_geometry = False
        self._grid.schedule()

    def eventFilter(self, watched, event):
        if self._disposed:
            return False
        if watched is self.dialog:
            if event.type() == QEvent.Resize:
                if not self._applying_size and not self._opening_geometry:
                    size = event.size()
                    if size.width() > 200 and size.height() > 200:
                        self._schedule_window_state_save()
            elif event.type() == QEvent.Move:
                if self.debug:
                    self._log(
                        f"[PBE] event move geom=({self.dialog.x()},{self.dialog.y()},{self.dialog.width()}x{self.dialog.height()})"
                    )
                if not self._applying_size and not self._opening_geometry:
                    self._schedule_window_state_save()
            elif event.type() == QEvent.Show and self.debug:
                self._log(
                    f"[PBE] event show vis={self.dialog.isVisible()} geom=({self.dialog.x()},{self.dialog.y()},{self.dialog.width()}x{self.dialog.height()})"
                )
            elif event.type() in (QEvent.Close, QEvent.Hide, QEvent.DeferredDelete):
                # setWindowFlags can hide a window during the opening adapter.
                if event.type() != QEvent.Hide or not getattr(self.dialog, "_pbe_in_show", False):
                    self._finish_window_session()
                if event.type() == QEvent.DeferredDelete:
                    self._release_grid_before_delete()
                if self.debug:
                    self._log(f"[PBE] window session end: {event.type()}")
        return False

    def _apply_saved_dialog_pos(self):
        if self._disposed:
            return
        state = self._window_state.read()
        self.fit_dialog_to_screen(position=state["pos"] if state else None)

    def fit_dialog_to_screen(self, position=None, size=None):
        if self._disposed:
            return
        was_applying_size = self._applying_size
        try:
            self._applying_size = True
            fit_window(self.dialog, position=position, size=size,
                       move=getattr(self.dialog, "_pbe_orig_move", None))
            self.record_restored_geometry()
        finally:
            self._applying_size = was_applying_size

    def has_saved_window_state(self):
        return self._window_state.read() is not None

    def apply_saved_dialog_state(self):
        if self._disposed:
            return False
        state = self._window_state.read()
        if not state:
            return False
        try:
            self.fit_dialog_to_screen(position=state["pos"],
                                      size=QSize(max(300, state["size"][0]), max(200, state["size"][1])))
            if self.debug:
                self._log(f"[PBE] restored frame={self.dialog.frameGeometry()}")
        except Exception:
            return False
        return True

    def _schedule_window_state_save(self):
        if self._disposed or not self.dialog.isVisible():
            return
        # Refresh the snapshot on every event, even while the timer is pending.
        self._capture_window_state()
        if self._pending_window_save and not self._save_timer.isActive():
            self._save_timer.start(WINDOW_STATE_DEBOUNCE_MS)

    def _save_window_state(self):
        if self._disposed:
            return
        self._save_timer.stop()
        self._capture_window_state()
        self._write_pending_window_state()

    def _capture_window_state(self):
        try:
            data = self._current_window_state()
        except RuntimeError:
            return
        if min(data["size"]) <= 200 or data == self._last_window_geometry:
            return
        self._last_window_geometry = data
        self._pending_window_state = data
        self._pending_window_save = True

    def _current_window_state(self):
        return {
            "pos": [self.dialog.x(), self.dialog.y()],
            "size": [self.dialog.width(), self.dialog.height()],
        }

    def _write_pending_window_state(self):
        if not self._pending_window_save:
            return
        try:
            self._window_state.write(self._pending_window_state)
        except Exception as exc:
            # Keep the snapshot for a later flush; never interrupt the UI.
            self._log(f"[PBE] window state save failed ({self._window_state.path}): {exc}", level=logging.ERROR)
            return
        self._pending_window_save = False
        self._pending_window_state = None

    def _resize_project_cards(self):
        self._grid.schedule()

    def _on_grid_columns_changed(self, columns):
        if self._disposed:
            return
        try:
            self._grid_preferences.write_columns(columns)
        except OSError as exc:
            self._log(f"[PBE] grid preference save failed ({self._grid_preferences.path}): {exc}", level=logging.ERROR)
        self._patches.plugin.set_grid_columns(columns)

    def set_grid_columns(self, columns):
        if self._disposed:
            return
        self._summary.set_columns(columns)
        self._grid.set_columns(columns)
