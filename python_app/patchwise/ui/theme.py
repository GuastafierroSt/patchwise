"""Alexandria editorial QSS theme tokens for PatchWise Desktop (PySide6)."""

ALEXANDRIA_TOKENS = {
    "surface": "#faf9fa",
    "surface_low": "#f5f3f4",
    "surface_lowest": "#ffffff",
    "surface_container": "#efedee",
    "surface_high": "#e9e8e9",
    "surface_highest": "#e3e2e3",
    "primary": "#094cb2",
    "primary_container": "#3366cc",
    "primary_fixed": "#d9e2ff",
    "on_primary": "#ffffff",
    "tertiary": "#6d5e00",
    "tertiary_fixed": "#f9e37a",
    "error": "#ba1a1a",
    "error_container": "#ffdad6",
    "on_surface": "#1b1c1d",
    "on_surface_variant": "#434653",
    "outline": "#737784",
}

ALEXANDRIA_QSS = """
QMainWindow, QWidget {
    background-color: #faf9fa;
    color: #1b1c1d;
    font-family: "Public Sans", "Segoe UI", sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #f5f3f4;
    border: none;
}

QFrame#Card, QFrame#HeroCard, QFrame#KpiCard, QFrame#ProgressBanner {
    background-color: #ffffff;
    border-radius: 12px;
    border: none;
}

QFrame#ProgressBanner {
    background-color: #f5f3f4;
}

QLabel#Headline {
    font-family: "Noto Serif", Georgia, serif;
    font-size: 26px;
    font-weight: 700;
    color: #1b1c1d;
    background: transparent;
}

QLabel#SectionTitle {
    font-family: "Noto Serif", Georgia, serif;
    font-size: 19px;
    font-weight: 700;
    color: #1b1c1d;
    background: transparent;
}

QLabel#CardTitle {
    font-family: "Noto Serif", Georgia, serif;
    font-size: 15px;
    font-weight: 700;
    color: #1b1c1d;
    background: transparent;
}

QLabel#MutedText {
    color: #434653;
    font-size: 12px;
    background: transparent;
}

QLabel#MonoVersion {
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
    font-weight: 600;
    color: #094cb2;
    background: transparent;
}

QPushButton#NavButton {
    text-align: left;
    padding: 10px 14px;
    border-radius: 10px;
    border: none;
    background-color: transparent;
    color: #434653;
    font-weight: 500;
}

QPushButton#NavButton:hover {
    background-color: #e9e8e9;
    color: #1b1c1d;
}

QPushButton#NavButton[active="true"] {
    background-color: #3366cc;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #094cb2, stop:1 #3366cc);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #094cb2;
}

QPushButton#PrimaryButton:disabled {
    background-color: #e3e2e3;
    color: #737784;
}

QPushButton#SecondaryButton {
    background-color: #e9e8e9;
    color: #1b1c1d;
    border: none;
    border-radius: 10px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton#SecondaryButton:hover {
    background-color: #e3e2e3;
}

QLineEdit#SearchInput {
    background-color: #ffffff;
    border: 1px solid rgba(195, 198, 213, 0.35);
    border-radius: 10px;
    padding: 7px 14px;
    color: #1b1c1d;
}

QLineEdit#SearchInput:focus {
    border: 1px solid #094cb2;
}

QProgressBar#DownloadBar {
    background-color: #e3e2e3;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar#DownloadBar::chunk {
    background-color: #094cb2;
    border-radius: 4px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
"""
