"""
Modern Dark Slate QSS Styling for SIG Vector Studio.
"""

DARK_THEME_QSS = """
/* Global Window & Typography */
QMainWindow, QDialog, QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* ToolBar & Action Buttons */
QToolBar {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    spacing: 6px;
    padding: 6px 10px;
}
QToolButton {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}
QToolButton:hover {
    background-color: #475569;
    border-color: #64748b;
}
QToolButton:pressed, QToolButton:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
}

/* Dock Widgets */
QDockWidget {
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    font-weight: 600;
    color: #94a3b8;
}
QDockWidget::title {
    background: #1e293b;
    padding: 8px 12px;
    border-bottom: 1px solid #334155;
    border-top: 1px solid #334155;
}

/* GroupBox & Frames */
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    background-color: #1e293b;
    font-weight: 600;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

/* Buttons */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#btnSuccess {
    background-color: #059669;
}
QPushButton#btnSuccess:hover {
    background-color: #047857;
}
QPushButton#btnDanger {
    background-color: #dc2626;
}
QPushButton#btnDanger:hover {
    background-color: #b91c1c;
}
QPushButton#btnSecondary {
    background-color: #334155;
    color: #e2e8f0;
    border: 1px solid #475569;
}
QPushButton#btnSecondary:hover {
    background-color: #475569;
}

/* Input Fields & Combos */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #090d16;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #0284c7;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #38bdf8;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
    selection-background-color: #0284c7;
}

/* Tables & Trees */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #090d16;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #1e293b;
    alternate-background-color: #0f172a;
}
QHeaderView::section {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 6px 8px;
    border: 1px solid #334155;
    font-weight: 600;
}
QTableWidget::item:selected, QTreeWidget::item:selected {
    background-color: #0284c7;
    color: #ffffff;
}

/* Status Bar */
QStatusBar {
    background-color: #1e293b;
    color: #94a3b8;
    border-top: 1px solid #334155;
    font-size: 12px;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
    padding: 4px 8px;
    font-size: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0f172a;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
