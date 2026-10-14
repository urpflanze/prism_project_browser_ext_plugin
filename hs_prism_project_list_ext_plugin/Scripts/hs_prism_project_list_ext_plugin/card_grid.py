# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

"""Responsive Qt card layout; Prism still owns the cards and their actions."""

import weakref

from qtpy.QtCore import QEvent, QObject, QRectF, QTimer, Qt
from qtpy.QtGui import QPainter, QPainterPath
from qtpy.QtWidgets import QSizePolicy


CARD_ASPECT = 4.0 / 3.0
GRID_MARGIN = 9
GRID_SPACING = 10


def paint_fitted_preview(label, card):
    """Paint the cached source on Prism's existing label, without cropping."""
    pixmap = getattr(card, "validPreview", None)
    if pixmap is None or pixmap.isNull():
        movie = label.movie()
        pixmap = movie.currentPixmap() if movie else label.pixmap()
    if pixmap is None or pixmap.isNull():
        return
    painter = QPainter(label)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(label.rect()), 8, 8)
    painter.setClipPath(clip)
    scale = min(label.width() / float(pixmap.width()), label.height() / float(pixmap.height()))
    width, height = pixmap.width() * scale, pixmap.height() * scale
    target = QRectF((label.width() - width) / 2, (label.height() - height) / 2, width, height)
    painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
    painter.end()


class ProjectCardGrid(QObject):
    def __init__(self, dialog, columns, parent):
        super(ProjectCardGrid, self).__init__(parent)
        self.dialog = dialog
        self.columns = columns
        self._disposed = False
        self._cards = []
        self._native_spacer = None
        self._states = weakref.WeakKeyDictionary()
        self._preview_cards = weakref.WeakKeyDictionary()
        self._extras = []
        self._layout = dialog.lo_projects
        self._original_margins = self._layout.contentsMargins()
        self._original_alignment = self._layout.alignment()
        self._original_spacing = self._layout.spacing()
        self._original_content_minimum = dialog.w_projects.minimumSize()
        self._original_content_maximum = dialog.w_projects.maximumSize()
        self._original_vertical_scroll_policy = dialog.sa_projects.verticalScrollBarPolicy()
        self._column_settings = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.reflow)
        dialog.sa_projects.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if not self._disposed and event.type() == QEvent.Paint:
            card_ref = self._preview_cards.get(watched)
            if card_ref is not None and card_ref() is not None:
                paint_fitted_preview(watched, card_ref())
                return True
        if (not self._disposed and self.dialog.isVisible()
                and event.type() in (QEvent.Resize, QEvent.Show, QEvent.FontChange)):
            self.schedule()
        return False

    def schedule(self):
        if not self._disposed:
            # refreshUi's callback happens before Prism adds its spacers.
            # Reflow on the next event-loop pass, once that layout is complete.
            self._timer.start(0)

    def set_columns(self, columns):
        self.columns = columns
        self.schedule()

    def _clear_extras(self):
        for widget, spacer, position in self._extras:
            if widget is not None:
                try:
                    widget.deleteLater()
                except RuntimeError:
                    pass
        self._extras = []

    def _prepare_card(self, card):
        if card in self._states:
            return
        original = card.l_preview
        self._states[card] = {
            "minimum": card.minimumSize(), "maximum": card.maximumSize(),
            "minHeight": card.minHeight, "previewHeight": card.previewHeight,
            "name_policy": card.l_name.sizePolicy(), "name_tooltip": card.l_name.toolTip(),
            "preview": original,
            "preview_minimum": original.minimumSize(), "preview_maximum": original.maximumSize(),
            "preview_policy": original.sizePolicy(),
            "footer_margins": card.lo_footer.contentsMargins(), "footer_spacing": card.lo_footer.spacing(),
            "name_stretch": card.lo_footer.stretch(card.lo_footer.indexOf(card.l_name)),
            "left_spacer": card.sp_left.sizeHint() if hasattr(card, "sp_left") else None,
        }
        self._preview_cards[original] = weakref.ref(card)
        original.installEventFilter(self)
        original.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        original.setMinimumWidth(0)
        card.l_name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        card.l_name.setToolTip(card.getDisplayName())
        card.lo_footer.setContentsMargins(4, 2, 4, 2)
        card.lo_footer.setSpacing(2)
        card.lo_footer.setStretchFactor(card.l_name, 1)
        if hasattr(card, "sp_left"):
            card.sp_left.changeSize(0, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)

    def reflow(self):
        if self._disposed:
            return
        self._timer.stop()
        cards = list(self.dialog.projectWidgets)
        native_spacer = getattr(self.dialog, "w_spacer", None)
        if cards != self._cards or native_spacer is not self._native_spacer:
            self._clear_extras()
            self._cards = cards
            self._native_spacer = native_spacer
        layout = self._layout
        # Remember native column constraints for unload; Qt retains empty
        # columns, so clear every column previously used by either layout.
        for column in range(max(layout.columnCount(), self.columns)):
            if column not in self._column_settings:
                self._column_settings[column] = (layout.columnMinimumWidth(column), layout.columnStretch(column))
            layout.setColumnMinimumWidth(column, 0)
            layout.setColumnStretch(column, 0)
        while layout.count():
            position = layout.getItemPosition(0)
            item = layout.takeAt(0)
            widget = item.widget()
            if widget not in cards:
                # Keep widgets/spacers, not obsolete QWidgetItem wrappers
                # from a layout which is about to be rebuilt.
                self._extras.append((widget, item if widget is None else None, position))
                if widget is not None:
                    widget.hide()
            del item
        layout.setContentsMargins(GRID_MARGIN, GRID_MARGIN, GRID_MARGIN, GRID_MARGIN)
        layout.setSpacing(GRID_SPACING)
        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        viewport = self.dialog.sa_projects.viewport()
        width = self._grid_width(len(cards))
        usable = max(self.columns, width - GRID_MARGIN * 2 - GRID_SPACING * (self.columns - 1))
        base, remainder = divmod(usable, self.columns)
        widths = [base + (1 if column < remainder else 0) for column in range(self.columns)]
        for column, card_width in enumerate(widths):
            layout.setColumnMinimumWidth(column, card_width)
        for index, card in enumerate(cards):
            self._prepare_card(card)
            card_width = widths[index % self.columns]
            card_height = max(1, round(card_width / CARD_ASPECT))
            footer_height = min(card_height - 1, max(23, card.l_name.fontMetrics().height() + 4))
            preview_height = max(1, card_height - footer_height)
            card.minHeight = card_height
            card.previewHeight = preview_height
            card.setFixedSize(card_width, card_height)
            card.l_preview.setFixedHeight(preview_height)
            layout.addWidget(card, index // self.columns, index % self.columns)
            card.lo_main.activate()
            card.l_name.setToolTip(card.getDisplayName())
            card.l_name.setText(card.l_name.fontMetrics().elidedText(card.getDisplayName(), Qt.ElideRight,
                                                                   max(0, card.l_name.width())))
            card.l_preview.update()
        rows = (len(cards) + self.columns - 1) // self.columns
        row_height = round(max(widths) / CARD_ASPECT)
        content_height = GRID_MARGIN * 2 + rows * row_height + max(0, rows - 1) * GRID_SPACING
        self.dialog.w_projects.setFixedWidth(width)
        self.dialog.w_projects.setFixedHeight(max(viewport.height(), content_height))
        layout.activate()

    def _grid_width(self, card_count):
        scroll_area = self.dialog.sa_projects
        if not self.dialog.isVisible():
            # Qt hides child scrollbars with their dialog. Match that hidden
            # viewport; the next Show schedules the visible layout again.
            return max(1, scroll_area.viewport().width())
        # Decide from the width WITHOUT a scrollbar. Otherwise the wider bar
        # can shrink the 4:3 cards enough to hide itself, then appear again as
        # the cards grow back, endlessly alternating at a height boundary.
        full_size = scroll_area.maximumViewportSize()
        scrollbar_width = scroll_area.verticalScrollBar().sizeHint().width()
        full_width = full_size.width()
        if scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOn:
            full_width += scrollbar_width
        rows = (card_count + self.columns - 1) // self.columns
        full_usable = max(self.columns, full_width - GRID_MARGIN * 2 - GRID_SPACING * (self.columns - 1))
        widest_card = (full_usable + self.columns - 1) // self.columns
        full_height = GRID_MARGIN * 2 + rows * round(widest_card / CARD_ASPECT) + max(0, rows - 1) * GRID_SPACING
        needs_scrollbar = full_height > full_size.height()
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn if needs_scrollbar else Qt.ScrollBarAlwaysOff)
        return max(1, full_width - (scrollbar_width if needs_scrollbar else 0))

    def stop(self):
        self._timer.stop()

    def abandon(self):
        # Called after the dialog's C++ widget has already been destroyed.
        self.stop()
        self._disposed = True
        # Keep Qt child wrappers until this QObject/controller is released.
        # Their native objects can still be inside Qt's child-destruction pass.
        self.dialog = None

    def dispose(self):
        if self._disposed:
            return
        self.stop()
        self._disposed = True
        dialog = self.dialog
        dialog.sa_projects.viewport().removeEventFilter(self)
        dialog.sa_projects.setVerticalScrollBarPolicy(self._original_vertical_scroll_policy)
        layout = self._layout
        # If unload occurs before a scheduled refresh, that refresh's native
        # layout is already in place and its old cards are no longer valid.
        if list(dialog.projectWidgets) == self._cards:
            while layout.count():
                layout.takeAt(0)
            for index, card in enumerate(self._cards):
                layout.addWidget(card, index // 3, index % 3 + 1)
            for widget, spacer, position in self._extras:
                if widget is not None:
                    layout.addWidget(widget, *position)
                    widget.show()
                else:
                    layout.addItem(spacer, *position)
            self._extras = []
        else:
            self._clear_extras()
        for column, (minimum, stretch) in self._column_settings.items():
            layout.setColumnMinimumWidth(column, minimum)
            layout.setColumnStretch(column, stretch)
        layout.setContentsMargins(self._original_margins)
        layout.setSpacing(self._original_spacing)
        layout.setAlignment(self._original_alignment)
        dialog.w_projects.setMinimumSize(self._original_content_minimum)
        dialog.w_projects.setMaximumSize(self._original_content_maximum)
        for card, state in list(self._states.items()):
            try:
                card.l_preview.removeEventFilter(self)
                card.l_preview.setMinimumSize(state["preview_minimum"])
                card.l_preview.setMaximumSize(state["preview_maximum"])
                card.l_preview.setSizePolicy(state["preview_policy"])
                card.setMinimumSize(state["minimum"])
                card.setMaximumSize(state["maximum"])
                card.minHeight, card.previewHeight = state["minHeight"], state["previewHeight"]
                card.l_name.setSizePolicy(state["name_policy"])
                card.l_name.setText(card.getDisplayName())
                card.l_name.setToolTip(state["name_tooltip"])
                card.lo_footer.setContentsMargins(state["footer_margins"])
                card.lo_footer.setSpacing(state["footer_spacing"])
                card.lo_footer.setStretchFactor(card.l_name, state["name_stretch"])
                if state["left_spacer"] is not None:
                    size = state["left_spacer"]
                    card.sp_left.changeSize(size.width(), size.height(), QSizePolicy.Fixed, QSizePolicy.Fixed)
                card.updateGeometry()
                if getattr(card, "validPreview", None):
                    card.updatePreview(load=False)
            except RuntimeError:
                # Prism may have destroyed a card during search/refresh.
                continue
        self._states.clear()
        self._preview_cards.clear()
        self._cards = []
        self.dialog = None
