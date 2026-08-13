import sys
import os
import cv2

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import (
    QImage,
    QPixmap,
    QFont,
    QPainter,
    QColor,
    QBrush,
    QPen,
    QImageReader
)
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QScrollArea,
    QDialog,
    QMessageBox,
    QFileDialog,
    QStackedWidget
)

from scanmedicine import (
    CameraStream,
    CameraError,
    save_frame_to_temp_file
)

from medicine_ai import (
    analyze_medicine_image,
    analyze_prescription_with_inventory,
    MedicineAIError,
    is_api_key_configured
)


COLOR_PRIMARY_BLUE = "#2878E8"
COLOR_DARK_NAVY = "#10244A"
COLOR_LIGHT_BLUE = "#EEF5FF"
COLOR_BORDER = "#DCE7F5"
COLOR_BACKGROUND = "#F9FBFE"
COLOR_TEXT_GRAY = "#536684"
COLOR_WHITE = "#FFFFFF"
COLOR_GREEN = "#1FAA59"
COLOR_RED = "#E4483A"

CAMERA_PREVIEW_WIDTH = 620
CAMERA_PREVIEW_HEIGHT = 460
CAMERA_TIMER_INTERVAL_MS = 30


# =========================================================
# SAFE IMAGE LOADER
# =========================================================

def load_pixmap_safe(image_path, width, height):
    """
    Safely loads an image and converts it to QPixmap.
    Returns an empty QPixmap if the image cannot be loaded.
    """

    pixmap = QPixmap()

    if not image_path:
        return pixmap

    try:
        image_path = os.path.abspath(str(image_path))

        if not os.path.exists(image_path):
            return pixmap

        reader = QImageReader(image_path)

        if not reader.canRead():
            return pixmap

        image = reader.read()

        if image.isNull():
            return pixmap

        pixmap = QPixmap.fromImage(image)

        if pixmap.isNull():
            return QPixmap()

        return pixmap.scaled(
            int(width),
            int(height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    except Exception:
        return QPixmap()


# =========================================================
# MEDICINE ANALYSIS WORKER
# =========================================================

class MedicineAnalysisWorker(QThread):

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def run(self):
        try:
            result = analyze_medicine_image(
                self.image_path
            )

            self.result_ready.emit(result)

        except MedicineAIError as exc:
            self.error_occurred.emit(
                exc.user_message
            )

        except Exception as exc:
            self.error_occurred.emit(
                f"Unexpected error: {exc}"
            )


# =========================================================
# PRESCRIPTION WORKER
# =========================================================

class PrescriptionWorker(QThread):

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        prescription_path,
        inventory,
        parent=None
    ):
        super().__init__(parent)

        self.prescription_path = prescription_path
        self.inventory = inventory

    def run(self):
        try:
            result = analyze_prescription_with_inventory(
                self.prescription_path,
                self.inventory
            )

            self.result_ready.emit(result)

        except MedicineAIError as exc:
            self.error_occurred.emit(
                exc.user_message
            )

        except Exception as exc:
            self.error_occurred.emit(
                f"Unexpected error: {exc}"
            )


# =========================================================
# SHIELD ICON
# =========================================================

class ShieldIcon(QWidget):

    def __init__(self, size=40, parent=None):
        super().__init__(parent)

        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        w = self._size
        h = self._size

        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF

        polygon = QPolygonF([
            QPointF(w * 0.5, h * 0.03),
            QPointF(w * 0.92, h * 0.20),
            QPointF(w * 0.92, h * 0.52),
            QPointF(w * 0.5, h * 0.97),
            QPointF(w * 0.08, h * 0.52),
            QPointF(w * 0.08, h * 0.20)
        ])

        painter.setBrush(
            QBrush(
                QColor(COLOR_PRIMARY_BLUE)
            )
        )

        painter.setPen(
            QPen(
                QColor(COLOR_DARK_NAVY),
                1
            )
        )

        painter.drawPolygon(polygon)

        painter.setBrush(
            QBrush(
                QColor(COLOR_WHITE)
            )
        )

        painter.setPen(Qt.NoPen)

        bar_w = w * 0.12
        bar_h = h * 0.42

        cx = w * 0.5
        cy = h * 0.48

        painter.drawRoundedRect(
            int(cx - bar_w / 2),
            int(cy - bar_h / 2),
            int(bar_w),
            int(bar_h),
            2,
            2
        )

        painter.drawRoundedRect(
            int(cx - bar_h / 2),
            int(cy - bar_w / 2),
            int(bar_h),
            int(bar_w),
            2,
            2
        )


# =========================================================
# MEDICINE CARD
# =========================================================

class MedicineCard(QFrame):

    def __init__(
        self,
        medicine_data,
        image_path,
        parent=None
    ):
        super().__init__(parent)

        self.medicine_data = medicine_data
        self.image_path = image_path

        self._build_ui()

    def _build_ui(self):

        self.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_WHITE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 14px;
            }}
        """)

        self.setMinimumWidth(300)
        self.setMaximumWidth(340)

        outer = QVBoxLayout(self)

        outer.setContentsMargins(
            16,
            16,
            16,
            16
        )

        outer.setSpacing(9)

        image = QLabel()

        image.setFixedHeight(150)

        image.setAlignment(
            Qt.AlignCenter
        )

        image.setStyleSheet(
            f"border: 1px solid {COLOR_BORDER};"
            f"border-radius: 10px;"
            f"background: {COLOR_LIGHT_BLUE};"
        )

        pixmap = load_pixmap_safe(
            self.image_path,
            300,
            150
        )

        if not pixmap.isNull():
            image.setPixmap(pixmap)
        else:
            image.setText(
                "Medicine Image"
            )

        outer.addWidget(image)

        name = self.medicine_data.get(
            "medicine_name",
            "Unknown"
        )

        dosage = self.medicine_data.get(
            "dosage",
            "Unknown"
        )

        unit = self.medicine_data.get(
            "dosage_unit",
            ""
        )

        title = name

        if dosage not in (
            "Unknown",
            "",
            "Not visible"
        ):
            title = (
                f"{name} {dosage} {unit}"
            ).strip()

        title_label = QLabel(title)

        title_label.setWordWrap(True)

        title_label.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 16px;"
            f"font-weight: 700;"
            f"border: none;"
        )

        outer.addWidget(title_label)

        try:
            confidence = float(
                self.medicine_data.get(
                    "confidence",
                    0
                )
            )
        except (
            TypeError,
            ValueError
        ):
            confidence = 0

        identified = (
            name not in (
                "Unknown",
                "",
                None
            )
            and confidence >= 0.4
        )

        status = QLabel(
            "✓  Medicine Identified"
            if identified
            else
            "⚠  Medicine Not Identified"
        )

        status.setStyleSheet(
            f"color: "
            f"{COLOR_GREEN if identified else COLOR_RED};"
            f"font-size: 12px;"
            f"font-weight: 600;"
            f"border: none;"
        )

        outer.addWidget(status)

        outer.addWidget(
            self._detail_row(
                "Active Ingredient:",
                self.medicine_data.get(
                    "active_ingredient",
                    "Unknown"
                )
            )
        )

        outer.addWidget(
            self._detail_row(
                "Dosage:",
                self._format_dosage()
            )
        )

        outer.addWidget(
            self._detail_row(
                "Manufacturer:",
                self.medicine_data.get(
                    "manufacturer",
                    "Unknown"
                )
            )
        )

        outer.addWidget(
            self._detail_row(
                "Type:",
                self.medicine_data.get(
                    "medicine_type",
                    "Unknown"
                )
            )
        )

        outer.addWidget(
            self._detail_row(
                "Package Size:",
                self.medicine_data.get(
                    "package_size",
                    "Unknown"
                )
            )
        )

        outer.addWidget(
            self._detail_row(
                "Confidence:",
                f"{int(confidence * 100)}%"
            )
        )

        description = self.medicine_data.get(
            "description",
            ""
        )

        if description and description not in (
            "Unknown",
            "Not visible"
        ):

            desc = QLabel(
                description
            )

            desc.setWordWrap(True)

            desc.setStyleSheet(
                f"color: {COLOR_TEXT_GRAY};"
                f"font-size: 12px;"
                f"border: none;"
            )

            outer.addWidget(desc)

        button = QPushButton(
            "View Details"
        )

        button.setCursor(
            Qt.PointingHandCursor
        )

        button.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_LIGHT_BLUE};
                color: {COLOR_PRIMARY_BLUE};
                border: 1px solid {COLOR_PRIMARY_BLUE};
                border-radius: 8px;
                padding: 8px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                background: {COLOR_PRIMARY_BLUE};
                color: {COLOR_WHITE};
            }}
        """)

        button.clicked.connect(
            self._open_details_dialog
        )

        outer.addWidget(button)

    def _format_dosage(self):

        dosage = self.medicine_data.get(
            "dosage",
            "Unknown"
        )

        unit = self.medicine_data.get(
            "dosage_unit",
            ""
        )

        if dosage in (
            "Unknown",
            "Not visible",
            ""
        ):
            return dosage or "Unknown"

        if unit and unit not in (
            "Unknown",
            "Not visible",
            ""
        ):
            return f"{dosage} {unit}"

        return dosage

    def _detail_row(
        self,
        label_text,
        value_text
    ):

        row = QWidget()

        row.setStyleSheet(
            "border: none;"
        )

        layout = QHBoxLayout(row)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(6)

        label = QLabel(
            label_text
        )

        label.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 12px;"
            f"font-weight: 600;"
            f"border: none;"
        )

        value = QLabel(
            str(value_text)
            if value_text
            else
            "Unknown"
        )

        value.setWordWrap(True)

        value.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 12px;"
            f"border: none;"
        )

        layout.addWidget(label)
        layout.addWidget(value, 1)

        return row

    def _open_details_dialog(self):

        MedicineDetailsDialog(
            self.medicine_data,
            self.image_path,
            self
        ).exec_()


# =========================================================
# MEDICINE DETAILS
# =========================================================

class MedicineDetailsDialog(QDialog):

    def __init__(
        self,
        medicine_data,
        image_path,
        parent=None
    ):
        super().__init__(parent)

        self.medicine_data = medicine_data
        self.image_path = image_path

        self.setWindowTitle(
            "Medicine Details"
        )

        self.setMinimumSize(
            420,
            560
        )

        self.setStyleSheet(
            f"background: {COLOR_WHITE};"
        )

        self._build_ui()

    def _build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            24,
            24,
            24
        )

        layout.setSpacing(12)

        image = QLabel()

        image.setFixedHeight(220)

        image.setAlignment(
            Qt.AlignCenter
        )

        image.setStyleSheet(
            f"border: 1px solid {COLOR_BORDER};"
            f"border-radius: 10px;"
            f"background: {COLOR_LIGHT_BLUE};"
        )

        pixmap = load_pixmap_safe(
            self.image_path,
            400,
            220
        )

        if not pixmap.isNull():
            image.setPixmap(pixmap)
        else:
            image.setText(
                "Medicine Image"
            )

        layout.addWidget(image)

        title = QLabel(
            self.medicine_data.get(
                "medicine_name",
                "Unknown"
            )
        )

        title.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 20px;"
            f"font-weight: 700;"
        )

        layout.addWidget(title)

        fields = [
            (
                "Active Ingredient",
                "active_ingredient"
            ),
            (
                "Dosage",
                None
            ),
            (
                "Manufacturer",
                "manufacturer"
            ),
            (
                "Medicine Type",
                "medicine_type"
            ),
            (
                "Package Size",
                "package_size"
            ),
            (
                "Description",
                "description"
            ),
            (
                "Confidence",
                None
            )
        ]

        for label_text, key in fields:

            if label_text == "Dosage":

                dosage = self.medicine_data.get(
                    "dosage",
                    "Unknown"
                )

                unit = self.medicine_data.get(
                    "dosage_unit",
                    ""
                )

                value = dosage

                if unit and unit not in (
                    "Unknown",
                    "Not visible",
                    ""
                ):
                    value = (
                        f"{dosage} {unit}"
                    )

            elif label_text == "Confidence":

                try:
                    confidence = float(
                        self.medicine_data.get(
                            "confidence",
                            0
                        )
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    confidence = 0

                value = (
                    f"{int(confidence * 100)}%"
                )

            else:

                value = self.medicine_data.get(
                    key,
                    "Unknown"
                )

            layout.addWidget(
                self._field_row(
                    label_text,
                    value
                )
            )

        visible = self.medicine_data.get(
            "visible_text",
            []
        )

        label = QLabel(
            "Visible Text"
        )

        label.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 12px;"
            f"font-weight: 700;"
        )

        layout.addWidget(label)

        text = QLabel(
            ", ".join(
                map(str, visible)
            )
            if visible
            else
            "Not visible"
        )

        text.setWordWrap(True)

        text.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 13px;"
        )

        layout.addWidget(text)

        layout.addStretch()

        close = QPushButton(
            "Close"
        )

        close.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_PRIMARY_BLUE};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
            }}
        """)

        close.clicked.connect(
            self.accept
        )

        layout.addWidget(close)

    def _field_row(
        self,
        label_text,
        value_text
    ):

        row = QWidget()

        layout = QVBoxLayout(row)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        label = QLabel(
            label_text
        )

        label.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 12px;"
            f"font-weight: 700;"
        )

        value = QLabel(
            str(value_text)
            if value_text
            else
            "Unknown"
        )

        value.setWordWrap(True)

        value.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 14px;"
        )

        layout.addWidget(label)
        layout.addWidget(value)

        return row


# =========================================================
# PRESCRIPTION RESULT CARD
# =========================================================

class PrescriptionResultCard(QFrame):

    def __init__(
        self,
        item,
        image_path=None,
        parent=None
    ):
        super().__init__(parent)

        available = bool(
            item.get(
                "available",
                False
            )
        )

        name = item.get(
            "prescription_name",
            "Unknown"
        )

        usage = item.get(
            "usage",
            "No usage instructions available."
        )

        matched_name = item.get(
            "matched_medicine_name",
            ""
        )

        self.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_WHITE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 14px;
            }}
        """)

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        layout.setSpacing(16)

        image = QLabel()

        image.setFixedSize(
            170,
            130
        )

        image.setAlignment(
            Qt.AlignCenter
        )

        image.setStyleSheet(
            f"background: {COLOR_LIGHT_BLUE};"
            f"border: 1px solid {COLOR_BORDER};"
            f"border-radius: 10px;"
        )

        if image_path:

            pixmap = load_pixmap_safe(
                image_path,
                170,
                130
            )

            if not pixmap.isNull():
                image.setPixmap(pixmap)
            else:
                image.setText(
                    "Medicine Image"
                )

        else:

            image.setText(
                "No Image"
            )

        layout.addWidget(image)

        info = QVBoxLayout()

        info.setSpacing(6)

        title = QLabel(name)

        title.setWordWrap(True)

        title.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 17px;"
            f"font-weight: 700;"
            f"border: none;"
        )

        info.addWidget(title)

        status = QLabel(
            "✓ Match"
            if available
            else
            "✕ Not Match"
        )

        status.setStyleSheet(
            f"color: "
            f"{COLOR_GREEN if available else COLOR_RED};"
            f"font-size: 14px;"
            f"font-weight: 700;"
            f"border: none;"
        )

        info.addWidget(status)

        if available and matched_name:

            matched = QLabel(
                f"Scanned Medicine: {matched_name}"
            )

            matched.setWordWrap(True)

            matched.setStyleSheet(
                f"color: {COLOR_TEXT_GRAY};"
                f"font-size: 12px;"
                f"border: none;"
            )

            info.addWidget(matched)

        if available:

            usage_title = QLabel(
                "How to use:"
            )

            usage_title.setStyleSheet(
                f"color: {COLOR_DARK_NAVY};"
                f"font-size: 13px;"
                f"font-weight: 700;"
                f"border: none;"
            )

            info.addWidget(
                usage_title
            )

            usage_label = QLabel(
                usage
            )

            usage_label.setWordWrap(True)

            usage_label.setStyleSheet(
                f"color: {COLOR_TEXT_GRAY};"
                f"font-size: 13px;"
                f"border: none;"
            )

            info.addWidget(
                usage_label
            )

        else:

            not_found = QLabel(
                "This medicine was not found "
                "in your scanned medicines."
            )

            not_found.setWordWrap(True)

            not_found.setStyleSheet(
                f"color: {COLOR_TEXT_GRAY};"
                f"font-size: 13px;"
                f"border: none;"
            )

            info.addWidget(
                not_found
            )

        info.addStretch()

        layout.addLayout(
            info,
            1
        )


# =========================================================
# MAIN WINDOW
# =========================================================

class MedCheckWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "MedCheck - Smart Medicine Scanner"
        )

        self.resize(
            1200,
            780
        )

        self.setStyleSheet(
            f"background: {COLOR_BACKGROUND};"
        )

        self.camera_stream = CameraStream(
            camera_index=0
        )

        self.camera_timer = QTimer(self)

        self.camera_timer.timeout.connect(
            self._update_camera_frame
        )

        self.latest_frame = None

        self.medicines = []
        self.medicine_cards = []

        self.captured_image_path = None

        self.analysis_worker = None
        self.prescription_worker = None

        self._build_ui()

        self._start_camera()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        self.pages = QStackedWidget()

        self.setCentralWidget(
            self.pages
        )

        self.main_page = (
            self._build_main_page()
        )

        self.prescription_page = (
            self._build_prescription_page()
        )

        self.pages.addWidget(
            self.main_page
        )

        self.pages.addWidget(
            self.prescription_page
        )

        self.pages.setCurrentWidget(
            self.main_page
        )

    def _build_header(
        self,
        back_button=False
    ):

        header = QWidget()

        layout = QHBoxLayout(header)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(12)

        if back_button:

            back = QPushButton(
                "← Back"
            )

            back.setCursor(
                Qt.PointingHandCursor
            )

            back.setFixedHeight(40)

            back.setStyleSheet(
                self._secondary_button_style()
            )

            back.clicked.connect(
                self._show_main_page
            )

            layout.addWidget(back)

        layout.addWidget(
            ShieldIcon(44)
        )

        title_box = QVBoxLayout()

        title_box.setSpacing(0)

        title = QLabel(
            f'<span style="color:{COLOR_DARK_NAVY};'
            f'font-weight:800;">Med</span>'
            f'<span style="color:{COLOR_PRIMARY_BLUE};'
            f'font-weight:800;">Check</span>'
        )

        font = QFont()

        font.setPointSize(20)

        title.setFont(font)

        subtitle = QLabel(
            "Smart Medicine Scanner"
        )

        subtitle.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 12px;"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)

        layout.addStretch()

        return header

    def _build_main_page(self):

        page = QWidget()

        root = QVBoxLayout(page)

        root.setContentsMargins(
            24,
            20,
            24,
            20
        )

        root.setSpacing(16)

        root.addWidget(
            self._build_header()
        )

        content = QHBoxLayout()

        content.setSpacing(20)

        content.addWidget(
            self._build_camera_panel(),
            0
        )

        content.addWidget(
            self._build_results_panel(),
            1
        )

        root.addLayout(
            content,
            1
        )

        return page

    def _build_camera_panel(self):

        panel = QFrame()

        panel.setFixedWidth(
            CAMERA_PREVIEW_WIDTH + 40
        )

        panel.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_WHITE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            20,
            20,
            20,
            20
        )

        layout.setSpacing(12)

        self.camera_label = QLabel(
            "Camera Ready"
        )

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setFixedSize(
            CAMERA_PREVIEW_WIDTH,
            CAMERA_PREVIEW_HEIGHT
        )

        self.camera_label.setStyleSheet(f"""
            background: {COLOR_LIGHT_BLUE};
            color: {COLOR_TEXT_GRAY};
            border: 2px dashed {COLOR_PRIMARY_BLUE};
            border-radius: 14px;
            font-size: 16px;
            font-weight: 600;
        """)

        layout.addWidget(
            self.camera_label
        )

        status_row = QHBoxLayout()

        self.status_dot = QLabel("●")

        self.status_text = QLabel(
            "Status: Ready to scan"
        )

        self.status_dot.setStyleSheet(
            f"color: {COLOR_PRIMARY_BLUE};"
            f"font-size: 14px;"
        )

        self.status_text.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 13px;"
            f"font-weight: 600;"
        )

        status_row.addWidget(
            self.status_dot
        )

        status_row.addWidget(
            self.status_text
        )

        status_row.addStretch()

        layout.addLayout(
            status_row
        )

        self.scan_button = QPushButton(
            "📷  Scan Medicine"
        )

        self.scan_button.setFixedHeight(48)

        self.scan_button.setCursor(
            Qt.PointingHandCursor
        )

        self.scan_button.setStyleSheet(
            self._primary_button_style()
        )

        self.scan_button.clicked.connect(
            self._on_scan_clicked
        )

        layout.addWidget(
            self.scan_button
        )

        self.add_medicine_button = QPushButton(
            "＋  Add Medicine"
        )

        self.add_medicine_button.setFixedHeight(44)

        self.add_medicine_button.setCursor(
            Qt.PointingHandCursor
        )

        self.add_medicine_button.setStyleSheet(
            self._secondary_button_style()
        )

        self.add_medicine_button.clicked.connect(
            self._on_add_medicine_clicked
        )

        layout.addWidget(
            self.add_medicine_button
        )

        prescription = QPushButton(
            "📋  Scan Prescription"
        )

        prescription.setFixedHeight(44)

        prescription.setCursor(
            Qt.PointingHandCursor
        )

        prescription.setStyleSheet(
            self._secondary_button_style()
        )

        prescription.clicked.connect(
            self._open_prescription_page
        )

        layout.addWidget(
            prescription
        )

        return panel

    def _build_results_panel(self):

        panel = QFrame()

        panel.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_WHITE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 16px;
            }}
        """)

        outer = QVBoxLayout(panel)

        outer.setContentsMargins(
            20,
            20,
            20,
            20
        )

        heading = QLabel(
            "Scanned Medicines"
        )

        heading.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 18px;"
            f"font-weight: 700;"
            f"border: none;"
        )

        outer.addWidget(heading)

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(True)

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; }"
        )

        self.scroll_area.setFrameShape(
            QFrame.NoFrame
        )

        self.cards_container = QWidget()

        self.cards_layout = QGridLayout(
            self.cards_container
        )

        self.cards_layout.setSpacing(16)

        self.cards_layout.setAlignment(
            Qt.AlignTop
        )

        self.empty_state_label = QLabel(
            "No medicine scanned yet"
        )

        self.empty_state_label.setAlignment(
            Qt.AlignCenter
        )

        self.empty_state_label.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 14px;"
            f"border: none;"
        )

        self.cards_layout.addWidget(
            self.empty_state_label,
            0,
            0,
            1,
            2
        )

        self.scroll_area.setWidget(
            self.cards_container
        )

        outer.addWidget(
            self.scroll_area,
            1
        )

        return panel

    # =====================================================
    # PRESCRIPTION PAGE
    # =====================================================

    def _build_prescription_page(self):

        page = QWidget()

        root = QVBoxLayout(page)

        root.setContentsMargins(
            24,
            20,
            24,
            20
        )

        root.setSpacing(16)

        root.addWidget(
            self._build_header(
                back_button=True
            )
        )

        title = QLabel(
            "Prescription Check"
        )

        title.setStyleSheet(
            f"color: {COLOR_DARK_NAVY};"
            f"font-size: 24px;"
            f"font-weight: 800;"
        )

        root.addWidget(title)

        subtitle = QLabel(
            "Upload a prescription image and compare it "
            "with the medicines you scanned in MedCheck."
        )

        subtitle.setWordWrap(True)

        subtitle.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 13px;"
        )

        root.addWidget(subtitle)

        self.prescription_upload_button = QPushButton(
            "📁  Upload Prescription Image"
        )

        self.prescription_upload_button.setFixedHeight(
            50
        )

        self.prescription_upload_button.setCursor(
            Qt.PointingHandCursor
        )

        self.prescription_upload_button.setStyleSheet(
            self._primary_button_style()
        )

        self.prescription_upload_button.clicked.connect(
            self._choose_prescription
        )

        root.addWidget(
            self.prescription_upload_button
        )

        self.prescription_file_label = QLabel(
            "No prescription selected"
        )

        self.prescription_file_label.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 13px;"
        )

        root.addWidget(
            self.prescription_file_label
        )

        self.prescription_status = QLabel("")

        self.prescription_status.setStyleSheet(
            f"color: {COLOR_PRIMARY_BLUE};"
            f"font-size: 13px;"
            f"font-weight: 600;"
        )

        root.addWidget(
            self.prescription_status
        )

        self.prescription_scroll = QScrollArea()

        self.prescription_scroll.setWidgetResizable(
            True
        )

        self.prescription_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.prescription_scroll.setStyleSheet(
            "QScrollArea { border: none; }"
        )

        self.prescription_container = QWidget()

        self.prescription_layout = QVBoxLayout(
            self.prescription_container
        )

        self.prescription_layout.setSpacing(14)

        self.prescription_layout.setAlignment(
            Qt.AlignTop
        )

        self.prescription_empty = QLabel(
            "Upload a prescription to check availability."
        )

        self.prescription_empty.setAlignment(
            Qt.AlignCenter
        )

        self.prescription_empty.setStyleSheet(
            f"color: {COLOR_TEXT_GRAY};"
            f"font-size: 14px;"
        )

        self.prescription_layout.addWidget(
            self.prescription_empty
        )

        self.prescription_scroll.setWidget(
            self.prescription_container
        )

        root.addWidget(
            self.prescription_scroll,
            1
        )

        return page

    # =====================================================
    # BUTTON STYLES
    # =====================================================

    @staticmethod
    def _primary_button_style():

        return f"""
            QPushButton {{
                background: {COLOR_PRIMARY_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton:hover {{
                background: {COLOR_DARK_NAVY};
            }}

            QPushButton:disabled {{
                background: {COLOR_BORDER};
                color: {COLOR_TEXT_GRAY};
            }}
        """

    @staticmethod
    def _secondary_button_style():

        return f"""
            QPushButton {{
                background: {COLOR_WHITE};
                color: {COLOR_PRIMARY_BLUE};
                border: 1.5px solid {COLOR_PRIMARY_BLUE};
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton:hover {{
                background: {COLOR_LIGHT_BLUE};
            }}
        """

    # =====================================================
    # CAMERA STATUS
    # =====================================================

    def _set_status(
        self,
        text,
        color
    ):

        self.status_text.setText(
            f"Status: {text}"
        )

        self.status_text.setStyleSheet(
            f"color: {color};"
            f"font-size: 13px;"
            f"font-weight: 600;"
        )

        self.status_dot.setStyleSheet(
            f"color: {color};"
            f"font-size: 14px;"
        )

    # =====================================================
    # CAMERA
    # =====================================================

    def _start_camera(self):

        try:

            self.camera_stream.open()

        except CameraError as exc:

            self._set_status(
                str(exc),
                COLOR_RED
            )

            self.camera_label.setText(
                str(exc)
            )

            self.scan_button.setEnabled(
                False
            )

            return

        self.camera_timer.start(
            CAMERA_TIMER_INTERVAL_MS
        )

        self._set_status(
            "Ready to scan",
            COLOR_PRIMARY_BLUE
        )

    def _update_camera_frame(self):

        frame = self.camera_stream.read_frame()

        if frame is None:
            return

        self.latest_frame = frame.copy()

        try:

            display = cv2.resize(
                frame,
                (
                    CAMERA_PREVIEW_WIDTH,
                    CAMERA_PREVIEW_HEIGHT
                )
            )

            rgb = cv2.cvtColor(
                display,
                cv2.COLOR_BGR2RGB
            )

            h, w, ch = rgb.shape

            image = QImage(
                rgb.data,
                w,
                h,
                ch * w,
                QImage.Format_RGB888
            ).copy()

            pixmap = QPixmap.fromImage(
                image
            )

            if not pixmap.isNull():

                self.camera_label.setPixmap(
                    pixmap
                )

        except Exception as exc:

            self._set_status(
                f"Camera display error: {exc}",
                COLOR_RED
            )

    def _stop_camera(self):

        self.camera_timer.stop()

        try:
            self.camera_stream.release()
        except Exception:
            pass

    # =====================================================
    # SCAN MEDICINE
    # =====================================================

    def _on_scan_clicked(self):

        if self.latest_frame is None:

            QMessageBox.warning(
                self,
                "MedCheck",
                "Camera frame is not ready yet.\n"
                "Please wait a moment and try again."
            )

            return

        frame = self.latest_frame.copy()

        try:

            image_path = save_frame_to_temp_file(
                frame
            )

        except CameraError as exc:

            QMessageBox.warning(
                self,
                "MedCheck",
                str(exc)
            )

            return

        except Exception as exc:

            QMessageBox.warning(
                self,
                "MedCheck",
                f"Unable to save image:\n{exc}"
            )

            return

        if not image_path or not os.path.exists(
            image_path
        ):

            QMessageBox.warning(
                self,
                "MedCheck",
                "The captured image could not be saved."
            )

            return

        self.captured_image_path = image_path

        self._set_status(
            "Analyzing medicine...",
            COLOR_PRIMARY_BLUE
        )

        self.scan_button.setEnabled(
            False
        )

        self.analysis_worker = MedicineAnalysisWorker(
            image_path
        )

        self.analysis_worker.result_ready.connect(
            self._on_analysis_success
        )

        self.analysis_worker.error_occurred.connect(
            self._on_analysis_error
        )

        self.analysis_worker.start()

    def _on_analysis_success(
        self,
        result
    ):

        self.scan_button.setEnabled(
            True
        )

        name = result.get(
            "medicine_name",
            "Unknown"
        )

        try:

            confidence = float(
                result.get(
                    "confidence",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            confidence = 0

        if (
            name in (
                "Unknown",
                "",
                None
            )
            or confidence < 0.4
        ):

            self._set_status(
                "Unable to identify medicine",
                COLOR_RED
            )

        else:

            self._set_status(
                "Medicine identified",
                COLOR_GREEN
            )

        self.medicines.append({
            "data": result,
            "image_path": self.captured_image_path
        })

        self._add_medicine_card(
            result,
            self.captured_image_path
        )

    def _on_analysis_error(
        self,
        message
    ):

        self.scan_button.setEnabled(
            True
        )

        self._set_status(
            message,
            COLOR_RED
        )

        QMessageBox.warning(
            self,
            "MedCheck",
            message
        )

    def _add_medicine_card(
        self,
        data,
        image_path
    ):

        if self.empty_state_label is not None:

            self.cards_layout.removeWidget(
                self.empty_state_label
            )

            self.empty_state_label.deleteLater()

            self.empty_state_label = None

        card = MedicineCard(
            data,
            image_path
        )

        self.medicine_cards.append(
            card
        )

        index = (
            len(self.medicine_cards) - 1
        )

        row = index // 2
        col = index % 2

        self.cards_layout.addWidget(
            card,
            row,
            col
        )

    def _on_add_medicine_clicked(self):

        self._set_status(
            "Ready to scan",
            COLOR_PRIMARY_BLUE
        )

        self.scan_button.setEnabled(
            True
        )

    # =====================================================
    # PRESCRIPTION
    # =====================================================

    def _open_prescription_page(self):

        self.pages.setCurrentWidget(
            self.prescription_page
        )

    def _show_main_page(self):

        self.pages.setCurrentWidget(
            self.main_page
        )

    def _choose_prescription(self):

        if not is_api_key_configured():

            QMessageBox.warning(
                self,
                "MedCheck",
                "GEMINI_API_KEY is missing from .env"
            )

            return

        if not self.medicines:

            QMessageBox.information(
                self,
                "MedCheck",
                "Scan at least one medicine first, "
                "then upload the prescription."
            )

            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Prescription Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )

        if not path:
            return

        self.prescription_file_label.setText(
            f"Selected: {os.path.basename(path)}"
        )

        self.prescription_status.setText(
            "Comparing prescription with your scanned medicines..."
        )

        self.prescription_upload_button.setEnabled(
            False
        )

        self._clear_prescription_results()

        self.prescription_worker = PrescriptionWorker(
            path,
            self.medicines
        )

        self.prescription_worker.result_ready.connect(
            self._on_prescription_success
        )

        self.prescription_worker.error_occurred.connect(
            self._on_prescription_error
        )

        self.prescription_worker.start()

    def _clear_prescription_results(self):

        while self.prescription_layout.count():

            item = (
                self.prescription_layout.takeAt(0)
            )

            widget = item.widget()

            if widget:
                widget.deleteLater()

    # =====================================================
    # UPDATED PRESCRIPTION SUCCESS
    # MATCH ONLY
    # =====================================================

    def _on_prescription_success(
        self,
        result
    ):

        self.prescription_upload_button.setEnabled(
            True
        )

        self.prescription_status.setText(
            "Prescription checked successfully."
        )

        self._clear_prescription_results()

        items = result.get(
            "medicines",
            []
        )

        if not items:

            label = QLabel(
                "No matching medicines found."
            )

            label.setStyleSheet(
                f"color: {COLOR_TEXT_GRAY};"
                f"font-size: 14px;"
            )

            self.prescription_layout.addWidget(
                label
            )

            return

        matched_count = 0

        for item in items:

            # =========================================
            # SHOW MATCH ONLY
            # =========================================

            available = item.get(
                "available",
                False
            )

            if not available:
                continue

            index = item.get(
                "matched_medicine_index",
                -1
            )

            try:

                index = int(index)

            except (
                TypeError,
                ValueError
            ):

                index = -1

            image_path = None

            if 0 <= index < len(
                self.medicines
            ):

                image_path = (
                    self.medicines[index]
                    ["image_path"]
                )

                real_name = (
                    self.medicines[index]
                    ["data"]
                    .get(
                        "medicine_name",
                        "Unknown"
                    )
                )

                if real_name not in (
                    "",
                    "Unknown",
                    None
                ):

                    item[
                        "matched_medicine_name"
                    ] = real_name

            else:

                item[
                    "matched_medicine_name"
                ] = ""

            card = PrescriptionResultCard(
                item,
                image_path
            )

            self.prescription_layout.addWidget(
                card
            )

            matched_count += 1

        # =========================================
        # NO MATCHES AT ALL
        # =========================================

        if matched_count == 0:

            label = QLabel(
                "No matching medicines found."
            )

            label.setAlignment(
                Qt.AlignCenter
            )

            label.setStyleSheet(
                f"color: {COLOR_TEXT_GRAY};"
                f"font-size: 14px;"
            )

            self.prescription_layout.addWidget(
                label
            )

    def _on_prescription_error(
        self,
        message
    ):

        self.prescription_upload_button.setEnabled(
            True
        )

        self.prescription_status.setText(
            "Could not check prescription."
        )

        QMessageBox.warning(
            self,
            "MedCheck",
            message
        )

    # =====================================================
    # CLOSE
    # =====================================================

    def closeEvent(self, event):

        self._stop_camera()

        if (
            self.analysis_worker
            and self.analysis_worker.isRunning()
        ):

            self.analysis_worker.quit()

            self.analysis_worker.wait(
                1500
            )

        if (
            self.prescription_worker
            and self.prescription_worker.isRunning()
        ):

            self.prescription_worker.quit()

            self.prescription_worker.wait(
                1500
            )

        event.accept()


# =========================================================
# MAIN
# =========================================================

def main():

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "MedCheck"
    )

    window = MedCheckWindow()

    window.show()

    sys.exit(
        app.exec_()
    )


if __name__ == "__main__":
    main()