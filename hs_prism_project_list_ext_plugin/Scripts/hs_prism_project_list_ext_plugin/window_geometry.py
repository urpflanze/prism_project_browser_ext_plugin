# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

"""Qt window fitting in logical pixels, independent of Prism and persistence."""

from qtpy.QtCore import QPoint, QRect
from qtpy.QtWidgets import QApplication


def available_screen_rect(position, size):
    screens = QApplication.screens()
    if not screens:
        return None
    return select_available_rect(position, size, [screen.availableGeometry() for screen in screens],
                                 QApplication.primaryScreen().availableGeometry())


def select_available_rect(position, size, rectangles, primary):
    """Keep an existing monitor; prefer overlap when the old anchor is in a gap."""
    point = QPoint(*position)
    for rect in rectangles:
        if rect.contains(point):
            return rect
    old_frame = QRect(point, size)
    overlaps = [old_frame.intersected(rect) for rect in rectangles]
    areas = [max(0, overlap.width()) * max(0, overlap.height()) for overlap in overlaps]
    if areas and max(areas) > 0:
        return rectangles[areas.index(max(areas))]
    return primary


def fitted_position(position, frame_size, available):
    # QRect.right/bottom are inclusive. An oversized frame is anchored at the
    # top left so its title bar stays reachable even if a host enforces a minimum.
    return QPoint(
        max(available.left(), min(position[0], available.x() + available.width() - frame_size.width())),
        max(available.top(), min(position[1], available.y() + available.height() - frame_size.height())),
    )


def fit_window(dialog, position=None, size=None, move=None):
    """Resize first, then clamp the actual frame (not the requested client size)."""
    position = position if position is not None else [dialog.x(), dialog.y()]
    requested_size = size if size is not None else dialog.size()
    available = available_screen_rect(position, requested_size)
    if available is None:
        return
    dialog.ensurePolished()
    dialog.layout().activate()
    frame = dialog.frameGeometry()
    border_width = max(0, frame.width() - dialog.width())
    border_height = max(0, frame.height() - dialog.height())
    dialog.resize(min(requested_size.width(), max(1, available.width() - border_width)),
                  min(requested_size.height(), max(1, available.height() - border_height)))
    dialog.layout().activate()
    target = fitted_position(position, dialog.frameGeometry().size(), available)
    (move or dialog.move)(target)
