# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QSpinBox, QVBoxLayout, QWidget

from .runtime import MAX_GRID_COLUMNS


class ScrollbarWidthOverride:
    """Override only this scrollbar's width; inherit Prism's other style rules."""

    def __init__(self, scroll_area):
        self._scroll_area = scroll_area
        self._rule = ""

    def set_width(self, width):
        # Qt can recreate the scrollbar during style/window changes.
        scrollbar = self._scroll_area.verticalScrollBar()
        current = scrollbar.styleSheet()
        base = current.replace(self._rule, "", 1) if self._rule else current
        self._rule = "\nQScrollBar:vertical { width: %dpx; }" % width if width is not None else ""
        stylesheet = base + self._rule
        if current != stylesheet:
            scrollbar.setStyleSheet(stylesheet)

    def dispose(self):
        self.set_width(None)
        self._scroll_area = None


class CurrentProjectBanner(QWidget):
    def __init__(self, parent=None):
        super(CurrentProjectBanner, self).__init__(parent)
        self.setObjectName("pbe_current_project")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        title = QLabel("Current Project")
        title.setObjectName("pbe_title")
        name = QLabel("")
        name.setObjectName("pbe_name")
        name.setWordWrap(True)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        path = QLabel("")
        path.setObjectName("pbe_path")
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path.setWordWrap(True)
        path.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        layout.addWidget(title)
        layout.addWidget(name)
        layout.addWidget(path)

        # Direkt referenciak, hogy frissitesnel ne kelljen keresgelni.
        self._title = title
        self._name = name
        self._path = path

        # Helyi stilus, hogy ne erintse a tobbi UI elemet.
        self.setStyleSheet(
            "QWidget#pbe_current_project {"
            "  background: #2d333b;"
            "  border: 1px solid #3d444d;"
            "  border-radius: 6px;"
            "}"
            "QLabel#pbe_title { font-weight: bold; }"
            "QLabel#pbe_path { color: #a7b0ba; }"
        )

    def set_project(self, name, path):
        # Legyen egyertelmu fallback, ha nincs aktiv projekt.
        if not name or name == "No active project":
            self._name.setText("No active project")
            self._path.setText("")
            self._name.setToolTip("")
            self._path.setToolTip("")
            return

        self._name.setText(name)
        self._path.setText(path)
        self._name.setToolTip(name)
        self._path.setToolTip(path)


class ProjectListSummary(QWidget):
    columnsChanged = Signal(int)

    def __init__(self, parent=None):
        super(ProjectListSummary, self).__init__(parent)
        self.setObjectName("pbe_summary")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(8)

        label = QLabel("")
        label.setObjectName("pbe_summary_label")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        layout.addWidget(label, 1)
        columns_label = QLabel("Cards per row:")
        columns = QSpinBox()
        columns.setObjectName("pbe_grid_columns")
        columns.setRange(1, MAX_GRID_COLUMNS)
        columns.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        columns.setValue(3)
        columns.setToolTip("Number of equal-sized project cards per row")
        columns.valueChanged.connect(self.columnsChanged.emit)
        layout.addWidget(columns_label)
        layout.addWidget(columns)
        self._columns = columns

        # Kozvetlen referencia a gyors frissiteshez.
        self._label = label

    def set_columns(self, columns):
        blocked = self._columns.blockSignals(True)
        self._columns.setValue(columns)
        self._columns.blockSignals(blocked)

    def set_summary(self, total_count, filter_text):
        # Kontextus megjelenitese a Prism widgetek modositas nelkul.
        if filter_text:
            text = "Projects: {0} (filter: {1})".format(total_count, filter_text)
        else:
            text = "Projects: {0}".format(total_count)
        self._label.setText(text)
