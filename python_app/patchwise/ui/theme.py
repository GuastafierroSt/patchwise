"""Modern sans-serif Light & Dark QSS themes built from the PatchWise logo palette."""

from __future__ import annotations

from typing import Dict

FONT_STACK_SANS = (
    '"Helvetica Neue", "Helvetica", "Inter", "Segoe UI Variable", "Segoe UI", "Arial", sans-serif'
)
FONT_STACK_MONO = '"Cascadia Code", "JetBrains Mono", "Consolas", monospace'

# Logo chromatic DNA:
# - Obsidian Violet Hex : #141028 / #17122c
# - Hexagon Rim Violet  : #6b58a3
# - Electric Cyan       : #11d2f2 / #3bdbf6
# - Royal Violet        : #685bd9
# - Vivid Purple        : #a451d6
# - Magenta Rose        : #e83061

LIGHT_TOKENS: Dict[str, str] = {
    "surface": "#f6f5fc",
    "sidebar_bg": "#ffffff",
    "sidebar_border": "#e6e2f3",
    "topbar_bg": "#ffffff",
    "card_bg": "#ffffff",
    "card_border": "#e8e4f5",
    "card_hover_border": "#a451d6",
    "banner_bg": "#f8f6fe",
    "banner_border": "#dfd7f8",
    "chip_bg": "#f2effb",
    "chip_border": "#e2dcf5",
    "chip_text": "#3f3761",
    "primary": "#5c4fd6",
    "primary_end": "#a451d6",
    "primary_hover": "#4b3ec4",
    "primary_hover_end": "#8e3cc2",
    "bar_start": "#06b6d4",
    "bar_mid": "#685bd9",
    "bar_end": "#e83061",
    "on_primary": "#ffffff",
    "secondary_bg": "#f1eefb",
    "secondary_hover": "#e5dff8",
    "secondary_border": "#ddd6f3",
    "secondary_text": "#17122c",
    "disabled_bg": "#ebe7f5",
    "disabled_text": "#9890b2",
    "nav_text": "#544c72",
    "nav_hover_bg": "#f4f1fc",
    "nav_hover_text": "#17122c",
    "nav_active_bg": "#f1ecff",
    "nav_active_text": "#5c4fd6",
    "nav_active_border": "#d6c8fb",
    "text_primary": "#17122c",
    "text_muted": "#645d80",
    "mono_text": "#0e7490",
    "mono_bg": "#ecfeff",
    "mono_border": "#a5f3fc",
    "input_bg": "#faf9fe",
    "input_border": "#ddd7f0",
    "input_focus_bg": "#ffffff",
    "input_placeholder": "#9890b2",
    "bar_bg": "#e6e1f4",
    "checkbox_bg": "#ffffff",
    "checkbox_border": "#c8c0e0",
    "checkbox_hover": "#685bd9",
    "scroll_handle": "#cec7e4",
    "scroll_handle_hover": "#a499c7",
    "icon_color": "#3d355e",
    "icon_active": "#5c4fd6",
    "icon_muted": "#726a90",
    "toast_success_bg": "#ecfdf5",
    "toast_success_border": "#6ee7b7",
    "toast_success_icon_bg": "#10b981",
    "toast_success_title": "#065f46",
    "toast_success_msg": "#047857",
    "toast_warning_bg": "#fff1f5",
    "toast_warning_border": "#fda4bd",
    "toast_warning_icon_bg": "#e83061",
    "toast_warning_title": "#881337",
    "toast_warning_msg": "#9f1239",
    "toast_close_text": "#544c72",
    "toast_close_hover": "rgba(23, 18, 44, 0.08)",
    "pill_security_bg": "#fff0f4",
    "pill_security_border": "#fbc8d7",
    "pill_security_text": "#c81e4f",
    "pill_features_bg": "#f5efff",
    "pill_features_border": "#e0ccff",
    "pill_features_text": "#7c3aed",
    "pill_patch_bg": "#ecfeff",
    "pill_patch_border": "#a5f3fc",
    "pill_patch_text": "#0e7490",
    "status_ok_bg": "#ecfdf5",
    "status_ok_text": "#047857",
    "status_ok_border": "#a7f3d0",
    "status_err_bg": "#fff0f4",
    "status_err_text": "#c81e4f",
    "status_err_border": "#fbc8d7",
    "status_cancel_bg": "#fffbeb",
    "status_cancel_text": "#b45309",
    "status_cancel_border": "#fde68a",
    "switch_track_off": "#cfc9e3",
    "switch_track_on": "#685bd9",
    "switch_thumb": "#ffffff",
}

DARK_TOKENS: Dict[str, str] = {
    "surface": "#0e0b1d",
    "sidebar_bg": "#141028",
    "sidebar_border": "#29224a",
    "topbar_bg": "#141028",
    "card_bg": "#1a1534",
    "card_border": "#2e2654",
    "card_hover_border": "#3bdbf6",
    "banner_bg": "#16122e",
    "banner_border": "#332a60",
    "chip_bg": "#211b40",
    "chip_border": "#362d63",
    "chip_text": "#d7d0f2",
    "primary": "#685bd9",
    "primary_end": "#a451d6",
    "primary_hover": "#7a6ee6",
    "primary_hover_end": "#b664e8",
    "bar_start": "#11d2f2",
    "bar_mid": "#685bd9",
    "bar_end": "#e83061",
    "on_primary": "#ffffff",
    "secondary_bg": "#221c42",
    "secondary_hover": "#2c2454",
    "secondary_border": "#3a3169",
    "secondary_text": "#f3f1fc",
    "disabled_bg": "#201a3b",
    "disabled_text": "#6b638f",
    "nav_text": "#a69ec9",
    "nav_hover_bg": "#221c42",
    "nav_hover_text": "#f6f4ff",
    "nav_active_bg": "rgba(104, 91, 217, 0.24)",
    "nav_active_text": "#3bdbf6",
    "nav_active_border": "rgba(164, 81, 214, 0.48)",
    "text_primary": "#f3f1fc",
    "text_muted": "#a198c7",
    "mono_text": "#3bdbf6",
    "mono_bg": "rgba(17, 210, 242, 0.12)",
    "mono_border": "rgba(59, 219, 246, 0.30)",
    "input_bg": "#110d24",
    "input_border": "#302857",
    "input_focus_bg": "#181332",
    "input_placeholder": "#766e9b",
    "bar_bg": "#261f47",
    "checkbox_bg": "#120e26",
    "checkbox_border": "#4d4282",
    "checkbox_hover": "#3bdbf6",
    "scroll_handle": "#393066",
    "scroll_handle_hover": "#544791",
    "icon_color": "#d4cdef",
    "icon_active": "#3bdbf6",
    "icon_muted": "#9c93c4",
    "toast_success_bg": "#082924",
    "toast_success_border": "#10b981",
    "toast_success_icon_bg": "#10b981",
    "toast_success_title": "#6ee7b7",
    "toast_success_msg": "#a7f3d0",
    "toast_warning_bg": "#2d1124",
    "toast_warning_border": "#e83061",
    "toast_warning_icon_bg": "#e83061",
    "toast_warning_title": "#fda4bd",
    "toast_warning_msg": "#fecdd9",
    "toast_close_text": "#d4cdef",
    "toast_close_hover": "rgba(243, 241, 252, 0.12)",
    "pill_security_bg": "rgba(232, 48, 97, 0.18)",
    "pill_security_border": "rgba(232, 48, 97, 0.45)",
    "pill_security_text": "#ff85a7",
    "pill_features_bg": "rgba(164, 81, 214, 0.20)",
    "pill_features_border": "rgba(164, 81, 214, 0.45)",
    "pill_features_text": "#d9a6ff",
    "pill_patch_bg": "rgba(17, 210, 242, 0.14)",
    "pill_patch_border": "rgba(59, 219, 246, 0.38)",
    "pill_patch_text": "#5ee7ff",
    "status_ok_bg": "rgba(16, 185, 129, 0.16)",
    "status_ok_text": "#6ee7b7",
    "status_ok_border": "rgba(52, 211, 153, 0.35)",
    "status_err_bg": "rgba(232, 48, 97, 0.18)",
    "status_err_text": "#ff85a7",
    "status_err_border": "rgba(232, 48, 97, 0.45)",
    "status_cancel_bg": "rgba(245, 158, 11, 0.16)",
    "status_cancel_text": "#fcd34d",
    "status_cancel_border": "rgba(251, 191, 36, 0.35)",
    "switch_track_off": "#362d61",
    "switch_track_on": "#685bd9",
    "switch_thumb": "#ffffff",
}


def get_theme_tokens(theme: str = "light") -> Dict[str, str]:
    """Return the token dictionary for the requested theme ('light' or 'dark')."""
    return DARK_TOKENS if theme == "dark" else LIGHT_TOKENS


def get_theme_qss(theme: str = "light") -> str:
    """Build the complete modern sans-serif QSS stylesheet for 'light' or 'dark'."""
    t = get_theme_tokens(theme)
    return f"""
QMainWindow, QWidget {{
    background-color: {t["surface"]};
    color: {t["text_primary"]};
    font-family: {FONT_STACK_SANS};
    font-size: 13px;
}}

QFrame#Sidebar {{
    background-color: {t["sidebar_bg"]};
    border: none;
    border-right: 1px solid {t["sidebar_border"]};
}}

QFrame#TopBar {{
    background-color: {t["topbar_bg"]};
    border: none;
    border-bottom: 1px solid {t["sidebar_border"]};
}}

QFrame#SidebarDivider {{
    background-color: {t["sidebar_border"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

QFrame#ThemeSwitchCard {{
    background-color: {t["chip_bg"]};
    border: 1px solid {t["chip_border"]};
    border-radius: 12px;
}}

QFrame#HeroCard {{
    background-color: {t["card_bg"]};
    border-radius: 16px;
    border: 1px solid {t["card_border"]};
}}

QFrame#Card {{
    background-color: {t["card_bg"]};
    border-radius: 14px;
    border: 1px solid {t["card_border"]};
}}

QFrame#Card:hover {{
    border: 1px solid {t["card_hover_border"]};
}}

QFrame#ProgressBanner {{
    background-color: {t["banner_bg"]};
    border-radius: 12px;
    border: 1px solid {t["banner_border"]};
}}

QLabel#BrandLogo {{
    background: transparent;
    border: none;
}}

QLabel#BrandTitle {{
    font-family: {FONT_STACK_SANS};
    font-size: 18px;
    font-weight: 800;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#NavGroupLabel {{
    font-family: {FONT_STACK_SANS};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    color: {t["text_muted"]};
    background: transparent;
    padding-left: 6px;
}}

QLabel#Headline {{
    font-family: {FONT_STACK_SANS};
    font-size: 24px;
    font-weight: 700;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#SectionTitle {{
    font-family: {FONT_STACK_SANS};
    font-size: 16px;
    font-weight: 700;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#CardTitle {{
    font-family: {FONT_STACK_SANS};
    font-size: 14px;
    font-weight: 700;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#BannerTitle {{
    font-family: {FONT_STACK_SANS};
    font-size: 13px;
    font-weight: 700;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#ThemeSwitchLabel {{
    font-family: {FONT_STACK_SANS};
    font-size: 13px;
    font-weight: 600;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#MutedText {{
    color: {t["text_muted"]};
    font-size: 12px;
    background: transparent;
}}

QLabel#TopBarPageTitle {{
    font-family: {FONT_STACK_SANS};
    font-size: 15px;
    font-weight: 700;
    color: {t["text_primary"]};
    background: transparent;
}}

QLabel#MonoVersion {{
    font-family: {FONT_STACK_MONO};
    font-size: 11.5px;
    font-weight: 600;
    color: {t["mono_text"]};
    background-color: {t["mono_bg"]};
    border: 1px solid {t["mono_border"]};
    border-radius: 6px;
    padding: 2px 8px;
}}

QLabel#PercentBadge {{
    font-family: {FONT_STACK_MONO};
    font-size: 12px;
    font-weight: 700;
    color: {t["mono_text"]};
    background-color: {t["mono_bg"]};
    border: 1px solid {t["mono_border"]};
    border-radius: 6px;
    padding: 2px 8px;
}}

QLabel#StatChip {{
    font-family: {FONT_STACK_SANS};
    font-size: 12px;
    font-weight: 600;
    color: {t["chip_text"]};
    background-color: {t["chip_bg"]};
    border: 1px solid {t["chip_border"]};
    border-radius: 8px;
    padding: 4px 10px;
}}

QLabel#CategoryPill {{
    font-family: {FONT_STACK_SANS};
    font-size: 11px;
    font-weight: 700;
    border-radius: 10px;
    padding: 2px 9px;
}}

QLabel#CategoryPill[category="security"] {{
    background-color: {t["pill_security_bg"]};
    border: 1px solid {t["pill_security_border"]};
    color: {t["pill_security_text"]};
}}

QLabel#CategoryPill[category="features"] {{
    background-color: {t["pill_features_bg"]};
    border: 1px solid {t["pill_features_border"]};
    color: {t["pill_features_text"]};
}}

QLabel#CategoryPill[category="patch"] {{
    background-color: {t["pill_patch_bg"]};
    border: 1px solid {t["pill_patch_border"]};
    color: {t["pill_patch_text"]};
}}

QLabel#HistoryStatusBadge {{
    font-family: {FONT_STACK_SANS};
    font-size: 12px;
    font-weight: 700;
    border-radius: 10px;
    padding: 4px 11px;
}}

QLabel#HistoryStatusBadge[status="success"] {{
    background-color: {t["status_ok_bg"]};
    border: 1px solid {t["status_ok_border"]};
    color: {t["status_ok_text"]};
}}

QLabel#HistoryStatusBadge[status="failed"] {{
    background-color: {t["status_err_bg"]};
    border: 1px solid {t["status_err_border"]};
    color: {t["status_err_text"]};
}}

QLabel#HistoryStatusBadge[status="cancelled"] {{
    background-color: {t["status_cancel_bg"]};
    border: 1px solid {t["status_cancel_border"]};
    color: {t["status_cancel_text"]};
}}

QPushButton#IconButton {{
    background-color: transparent;
    border: 1px solid {t["secondary_border"]};
    border-radius: 10px;
    padding: 6px;
    color: {t["text_primary"]};
}}

QPushButton#IconButton:hover {{
    background-color: {t["secondary_bg"]};
    border: 1px solid {t["card_hover_border"]};
}}

QPushButton#NavButton {{
    text-align: left;
    padding: 10px 14px;
    border-radius: 10px;
    border: 1px solid transparent;
    background-color: transparent;
    color: {t["nav_text"]};
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#NavButton:hover {{
    background-color: {t["nav_hover_bg"]};
    color: {t["nav_hover_text"]};
}}

QPushButton#NavButton[active="true"] {{
    background-color: {t["nav_active_bg"]};
    border: 1px solid {t["nav_active_border"]};
    color: {t["nav_active_text"]};
    font-weight: 700;
}}

QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t["primary"]}, stop:1 {t["primary_end"]});
    color: {t["on_primary"]};
    border: none;
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 700;
}}

QPushButton#PrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t["primary_hover"]}, stop:1 {t["primary_hover_end"]});
}}

QPushButton#PrimaryButton:disabled {{
    background: {t["disabled_bg"]};
    color: {t["disabled_text"]};
}}

QPushButton#SecondaryButton {{
    background-color: {t["secondary_bg"]};
    color: {t["secondary_text"]};
    border: 1px solid {t["secondary_border"]};
    border-radius: 10px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton#SecondaryButton:hover {{
    background-color: {t["secondary_hover"]};
}}

QPushButton#SecondaryButton:disabled {{
    background-color: {t["disabled_bg"]};
    border: 1px solid transparent;
    color: {t["disabled_text"]};
}}

QLineEdit#SearchInput {{
    background-color: {t["input_bg"]};
    border: 1px solid {t["input_border"]};
    border-radius: 10px;
    padding: 8px 14px;
    color: {t["text_primary"]};
    selection-background-color: {t["primary"]};
    selection-color: {t["on_primary"]};
}}

QLineEdit#SearchInput:focus {{
    background-color: {t["input_focus_bg"]};
    border: 1.5px solid {t["primary"]};
}}

QCheckBox {{
    spacing: 8px;
    background: transparent;
}}

QProgressBar#DownloadBar {{
    background-color: {t["bar_bg"]};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}

QProgressBar#DownloadBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {t["bar_start"]},
        stop:0.55 {t["bar_mid"]},
        stop:1 {t["bar_end"]}
    );
    border-radius: 5px;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 0 4px 0;
}}

QScrollBar::handle:vertical {{
    background: {t["scroll_handle"]};
    min-height: 32px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t["scroll_handle_hover"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}

QFrame#StatusToast {{
    border-radius: 14px;
    border: 1px solid {t["card_border"]};
    background-color: {t["card_bg"]};
}}

QFrame#StatusToast[level="success"] {{
    background-color: {t["toast_success_bg"]};
    border: 1px solid {t["toast_success_border"]};
}}

QFrame#StatusToast[level="warning"] {{
    background-color: {t["toast_warning_bg"]};
    border: 1px solid {t["toast_warning_border"]};
}}

QLabel#ToastIcon {{
    border-radius: 13px;
    font-weight: 700;
    font-size: 13px;
}}

QLabel#ToastIcon[level="success"] {{
    background-color: {t["toast_success_icon_bg"]};
    color: #ffffff;
}}

QLabel#ToastIcon[level="warning"] {{
    background-color: {t["toast_warning_icon_bg"]};
    color: #ffffff;
}}

QLabel#ToastTitle {{
    font-weight: 700;
    font-size: 13px;
    background: transparent;
}}

QLabel#ToastTitle[level="success"] {{
    color: {t["toast_success_title"]};
}}

QLabel#ToastTitle[level="warning"] {{
    color: {t["toast_warning_title"]};
}}

QLabel#ToastMessage {{
    font-size: 12px;
    background: transparent;
}}

QLabel#ToastMessage[level="success"] {{
    color: {t["toast_success_msg"]};
}}

QLabel#ToastMessage[level="warning"] {{
    color: {t["toast_warning_msg"]};
}}

QPushButton#ToastCloseButton {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 700;
    color: {t["toast_close_text"]};
    padding: 0px;
}}

QPushButton#ToastCloseButton:hover {{
    background-color: {t["toast_close_hover"]};
    color: {t["text_primary"]};
}}
"""


# Backward-compatible aliases
ALEXANDRIA_TOKENS = LIGHT_TOKENS
ALEXANDRIA_QSS = get_theme_qss("light")
