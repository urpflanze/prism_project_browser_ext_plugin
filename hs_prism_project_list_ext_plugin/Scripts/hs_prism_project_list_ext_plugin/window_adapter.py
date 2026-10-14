# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

"""Delegate opening to Prism, adapting only its direct geometry calls.

Code identity scopes the Qt overrides to the captured native methods. Events
dispatched by Prism's processEvents (including user moves) remain ordinary Qt
calls; no elapsed-time guard or replacement Prism UI logic is needed.
"""

import inspect
import os
import sys
import traceback

from qtpy.QtCore import Qt


def _native_code(method):
    return getattr(inspect.unwrap(method), "__code__", None)


def install_browser(plugin, browser):
    if getattr(browser, "_pbe_onprojects_patched", False):
        return
    original = browser.onProjectsClicked

    def open_projects(*args, **kwargs):
        plugin._log("[PBE] onProjectsClicked patch hit")
        dialog = getattr(browser, "w_projects", None)
        if dialog is not None:
            try:
                dialog.isVisible()
            except RuntimeError:
                del browser.w_projects
            else:
                if getattr(dialog, "_pbe_in_show", False):
                    return None
        return original(*args, **kwargs)

    plugin._patches.apply(browser, "onProjectsClicked", open_projects,
                          "_pbe_onprojects_patched")


def install_dialog(plugin, dialog):
    if getattr(dialog, "_pbe_showwidget_patched", False):
        return
    original_show = dialog.showWidget
    show_code = _native_code(original_show)
    browser_method = dialog.origin.onProjectsClicked
    patch = plugin.core.plugins.getFunctionPatch(browser_method)
    open_code = _native_code(patch["orig"] if patch else browser_method)
    controller = plugin._get_controller(dialog)

    # Refuse the whole geometry adapter if one required method is already
    # owned by another plugin. Never force a competing override away.
    names = ("showWidget", "setWindowFlags", "resize", "adjustSize", "move")
    if not all(plugin._patches.can_apply(dialog, name) for name in names):
        return
    original_flags = dialog.setWindowFlags
    original_resize = dialog.resize
    original_adjust = dialog.adjustSize
    original_move = dialog.move

    def set_flags(flags):
        if show_code is not None and sys._getframe(1).f_code is show_code:
            flags = Qt.WindowFlags(int(flags) & ~int(Qt.FramelessWindowHint))
        return original_flags(flags)

    def resize(*args):
        if show_code is not None and sys._getframe(1).f_code is show_code:
            return None  # Prism's final card-derived width replaces user size.
        return original_resize(*args)

    def adjust_size():
        if open_code is not None and sys._getframe(1).f_code is open_code:
            if controller.apply_saved_dialog_state():
                return None
            result = original_adjust()
            controller.fit_dialog_to_screen()
            return result
        return original_adjust()

    def move(*args):
        if plugin.debug:
            plugin._log(f"[PBE] move called, args={args}")
        if open_code is not None and sys._getframe(1).f_code is open_code:
            if controller.has_saved_window_state() or controller._pending_window_save:
                return None
            point = args[0] if len(args) == 1 else None
            position = [point.x(), point.y()] if point is not None else list(args)
            controller.fit_dialog_to_screen(position=position)
            return None
        return original_move(*args)

    def show_widget(*args, **kwargs):
        if not plugin._active:
            return original_show(*args, **kwargs)
        if getattr(dialog, "_pbe_in_show", False):
            plugin._log("[PBE] showWidget reentry blocked")
            return None
        if dialog.isVisible():
            plugin._log("[PBE] showWidget duplicate blocked")
            return None
        dialog._pbe_in_show = True
        controller._opening_geometry = True
        try:
            if plugin.debug:
                stack = traceback.extract_stack(limit=6)
                caller = " > ".join(
                    f"{frame.name}@{os.path.basename(frame.filename)}:{frame.lineno}"
                    for frame in stack[:-1]
                )
                plugin._log(f"[PBE] showWidget caller={caller}")
            if not controller.apply_saved_dialog_state():
                controller.fit_dialog_to_screen()
            return original_show(*args, **kwargs)
        finally:
            controller._opening_geometry = False
            if "_pbe_in_show" in dialog.__dict__:
                dialog._pbe_in_show = False

    for name, replacement, guard in (
        ("setWindowFlags", set_flags, "_pbe_flags_patched"),
        ("resize", resize, "_pbe_resize_patched"),
        ("adjustSize", adjust_size, "_pbe_adjust_patched"),
        ("move", move, "_pbe_move_wrapped"),
        ("showWidget", show_widget, "_pbe_showwidget_patched"),
    ):
        plugin._patches.apply(dialog, name, replacement, guard)
    dialog._pbe_orig_move = original_move
