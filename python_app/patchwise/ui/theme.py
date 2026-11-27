"""Apple Liquid Glass Light & Dark QSS themes built from the PatchWise logo palette."""

from __future__ import annotations

from typing import Dict

FONT_STACK_SANS = (
    '"Helvetica Neue", "Helvetica", "Inter", "Segoe UI Variable", "Segoe UI", "Arial", sans-serif'
)
FONT_STACK_MONO = '"Cascadia Code", "JetBrains Mono", "Consolas", monospace'

# Logo chromatic DNA:
# - Obsidian Violet Hex : #141028 / #17122c
# - Electric Cyan       : #11d2f2 / #3bdbf6
# - Royal Violet        : #685bd9
# - Vivid Purple        : #a451d6
# - Magenta Rose        : #e83061

LIGHT_TOKENS: Dict[str, str] = {
    "surface": "#f6f5fc",
    # Liquid Glass translucent frosted panels (light opal glass)
    "glass_sidebar_top": "rgba(255, 255, 255, 0.76)",
    "glass_sidebar_bot": "rgba(248, 246, 255, 0.62)",
    "glass_topbar_top": "rgba(255, 255, 255, 0.78)",
    "glass_topbar_bot": "rgba(250, 248, 255, 0.64)",
    "glass_hero_top": "rgba(255, 255, 255, 0.78)",
    "glass_hero_mid": "rgba(255, 255, 255, 0.64)",
    "glass_hero_bot": "rgba(248, 246, 255, 0.70)",
    "glass_card_top": "rgba(255, 255, 255, 0.84)",
    "glass_card_bot": "rgba(252, 250, 255, 0.66)",
    "glass_card_hover_top": "rgba(255, 255, 255, 0.94)",
    "glass_card_hover_bot": "rgba(246, 243, 255, 0.80)",
    "glass_popover_top": "rgba(255, 255, 255, 0.92)",
    "glass_popover_bot": "rgba(247, 244, 255, 0.88)",
    "glass_rim_top": "rgba(255, 255, 255, 0.96)",
    "glass_rim_left": "rgba(255, 255, 255, 0.82)",
    "glass_rim_right": "rgba(155, 142, 210, 0.28)",
    "glass_rim_bot": "rgba(128, 114, 194, 0.26)",
    "sidebar_border": "rgba(155, 142, 210, 0.24)",
    "card_border": "rgba(155, 142, 210, 0.24)",
    "card_hover_border": "rgba(104, 91, 217, 0.58)",
    "banner_bg": "rgba(255, 255, 255, 0.74)",
    "banner_border": "rgba(104, 91, 217, 0.28)",
    "chip_bg": "rgba(255, 255, 255, 0.62)",
    "chip_border": "rgba(255, 255, 255, 0.86)",
    "chip_border_bot": "rgba(140, 128, 200, 0.26)",
    "chip_text": "#352e54",
    "primary": "#5c4fd6",
    "primary_end": "#a451d6",
    "primary_hover": "#4b3ec4",
    "primary_hover_end": "#8e3cc2",
    "bar_start": "#06b6d4",
    "bar_mid": "#685bd9",
    "bar_end": "#e83061",
    "on_primary": "#ffffff",
    "secondary_bg": "rgba(255, 255, 255, 0.64)",
    "secondary_hover": "rgba(255, 255, 255, 0.88)",
    "secondary_border": "rgba(155, 142, 210, 0.30)",
    "secondary_text": "#17122c",
    "disabled_bg": "rgba(230, 226, 245, 0.55)",
    "disabled_text": "#9890b2",
    "nav_text": "#4d456b",
    "nav_hover_bg": "rgba(255, 255, 255, 0.55)",
    "nav_hover_text": "#17122c",
    "nav_active_bg": "rgba(104, 91, 217, 0.14)",
    "nav_active_text": "#4f42c9",
    "nav_active_border": "rgba(104, 91, 217, 0.32)",
    "text_primary": "#17122c",
    "text_muted": "#5c5478",
    "mono_text": "#0c6e8a",
    "mono_bg": "rgba(17, 210, 242, 0.13)",
    "mono_border": "rgba(17, 210, 242, 0.34)",
    "input_bg": "rgba(255, 255, 255, 0.60)",
    "input_border": "rgba(155, 142, 210, 0.32)",
    "input_focus_bg": "rgba(255, 255, 255, 0.90)",
    "input_placeholder": "#8c84a8",
    "bar_bg": "rgba(104, 91, 217, 0.14)",
    "checkbox_bg": "rgba(255, 255, 255, 0.78)",
    "checkbox_border": "#b9b0d8",
    "checkbox_hover": "#685bd9",
    "scroll_handle": "rgba(104, 91, 217, 0.28)",
    "scroll_handle_hover": "rgba(104, 91, 217, 0.48)",
    "icon_color": "#383059",
    "icon_active": "#5c4fd6",
    "icon_muted": "#6c638c",
    "toast_success_bg": "rgba(236, 253, 245, 0.90)",
    "toast_success_border": "rgba(16, 185, 129, 0.45)",
    "toast_success_icon_bg": "#10b981",
    "toast_success_title": "#065f46",
    "toast_success_msg": "#047857",
    "toast_warning_bg": "rgba(255, 241, 245, 0.92)",
    "toast_warning_border": "rgba(232, 48, 97, 0.45)",
    "toast_warning_icon_bg": "#e83061",
    "toast_warning_title": "#881337",
    "toast_warning_msg": "#9f1239",
    "toast_close_text": "#544c72",
    "toast_close_hover": "rgba(23, 18, 44, 0.08)",
    "pill_security_bg": "rgba(232, 48, 97, 0.11)",
    "pill_security_border": "rgba(232, 48, 97, 0.32)",
    "pill_security_text": "#be1849",
    "pill_features_bg": "rgba(164, 81, 214, 0.12)",
    "pill_features_border": "rgba(164, 81, 214, 0.34)",
    "pill_features_text": "#7c3aed",
    "pill_patch_bg": "rgba(17, 210, 242, 0.13)",
    "pill_patch_border": "rgba(17, 210, 242, 0.36)",
    "pill_patch_text": "#0c6e8a",
    "status_ok_bg": "rgba(16, 185, 129, 0.13)",
    "status_ok_text": "#047857",
    "status_ok_border": "rgba(16, 185, 129, 0.36)",
    "status_err_bg": "rgba(232, 48, 97, 0.12)",
    "status_err_text": "#be1849",
    "status_err_border": "rgba(232, 48, 97, 0.34)",
    "status_cancel_bg": "rgba(245, 158, 11, 0.14)",
    "status_cancel_text": "#b45309",
    "status_cancel_border": "rgba(245, 158, 11, 0.36)",
    "switch_track_off": "#cbc4e0",
    "switch_track_on": "#685bd9",
    "switch_thumb": "#ffffff",
}

DARK_TOKENS: Dict[str, str] = {
    "surface": "#0e0b1d",
    # Liquid Glass translucent dark obsidian crystal
    "glass_sidebar_top": "rgba(24, 19, 48, 0.72)",
    "glass_sidebar_bot": "rgba(16, 12, 34, 0.64)",
    "glass_topbar_top": "rgba(26, 20, 52, 0.74)",
    "glass_topbar_bot": "rgba(18, 14, 38, 0.64)",
    "glass_hero_top": "rgba(38, 31, 74, 0.60)",
    "glass_hero_mid": "rgba(26, 20, 54, 0.52)",
    "glass_hero_bot": "rgba(20, 16, 44, 0.58)",
    "glass_card_top": "rgba(255, 255, 255, 0.085)",
    "glass_card_bot": "rgba(255, 255, 255, 0.035)",
    "glass_card_hover_top": "rgba(255, 255, 255, 0.135)",
    "glass_card_hover_bot": "rgba(255, 255, 255, 0.065)",
    "glass_popover_top": "rgba(30, 24, 62, 0.90)",
    "glass_popover_bot": "rgba(20, 16, 44, 0.88)",
    "glass_rim_top": "rgba(255, 255, 255, 0.24)",
    "glass_rim_left": "rgba(255, 255, 255, 0.14)",
    "glass_rim_right": "rgba(255, 255, 255, 0.08)",
    "glass_rim_bot": "rgba(255, 255, 255, 0.06)",
    "sidebar_border": "rgba(255, 255, 255, 0.12)",
    "card_border": "rgba(255, 255, 255, 0.12)",
    "card_hover_border": "rgba(59, 219, 246, 0.58)",
    "banner_bg": "rgba(34, 27, 68, 0.62)",
    "banner_border": "rgba(59, 219, 246, 0.28)",
    "chip_bg": "rgba(255, 255, 255, 0.075)",
    "chip_border": "rgba(255, 255, 255, 0.18)",
    "chip_border_bot": "rgba(255, 255, 255, 0.07)",
    "chip_text": "#e4dff9",
    "primary": "#685bd9",
    "primary_end": "#a451d6",
    "primary_hover": "#7a6ee6",
    "primary_hover_end": "#b664e8",
    "bar_start": "#11d2f2",
    "bar_mid": "#685bd9",
    "bar_end": "#e83061",
    "on_primary": "#ffffff",
    "secondary_bg": "rgba(255, 255, 255, 0.08)",
    "secondary_hover": "rgba(255, 255, 255, 0.15)",
    "secondary_border": "rgba(255, 255, 255, 0.16)",
    "secondary_text": "#f5f3ff",
    "disabled_bg": "rgba(255, 255, 255, 0.05)",
    "disabled_text": "#746c99",
    "nav_text": "#b8b0db",
    "nav_hover_bg": "rgba(255, 255, 255, 0.08)",
    "nav_hover_text": "#ffffff",
    "nav_active_bg": "rgba(104, 91, 217, 0.28)",
    "nav_active_text": "#3bdbf6",
    "nav_active_border": "rgba(59, 219, 246, 0.42)",
    "text_primary": "#f5f3ff",
    "text_muted": "#b2a9d6",
    "mono_text": "#3bdbf6",
    "mono_bg": "rgba(17, 210, 242, 0.13)",
    "mono_border": "rgba(59, 219, 246, 0.34)",
    "input_bg": "rgba(12, 9, 28, 0.48)",
    "input_border": "rgba(255, 255, 255, 0.15)",
    "input_focus_bg": "rgba(20, 16, 44, 0.72)",
    "input_placeholder": "#867ead",
    "bar_bg": "rgba(255, 255, 255, 0.10)",
    "checkbox_bg": "rgba(255, 255, 255, 0.07)",
    "checkbox_border": "rgba(255, 255, 255, 0.26)",
    "checkbox_hover": "#3bdbf6",
    "scroll_handle": "rgba(255, 255, 255, 0.20)",
    "scroll_handle_hover": "rgba(255, 255, 255, 0.35)",
    "icon_color": "#e2dcf8",
    "icon_active": "#3bdbf6",
    "icon_muted": "#aba2d1",
    "toast_success_bg": "rgba(8, 42, 36, 0.88)",
    "toast_success_border": "rgba(16, 185, 129, 0.55)",
    "toast_success_icon_bg": "#10b981",
    "toast_success_title": "#6ee7b7",
    "toast_success_msg": "#d1fae5",
    "toast_warning_bg": "rgba(48, 16, 36, 0.90)",
    "toast_warning_border": "rgba(232, 48, 97, 0.60)",
    "toast_warning_icon_bg": "#e83061",
    "toast_warning_title": "#fda4bd",
    "toast_warning_msg": "#ffe4ec",
    "toast_close_text": "#d4cdef",
    "toast_close_hover": "rgba(245, 243, 255, 0.14)",
    "pill_security_bg": "rgba(232, 48, 97, 0.20)",
    "pill_security_border": "rgba(232, 48, 97, 0.48)",
    "pill_security_text": "#ff8cad",
    "pill_features_bg": "rgba(164, 81, 214, 0.22)",
    "pill_features_border": "rgba(164, 81, 214, 0.48)",
    "pill_features_text": "#e2b8ff",
    "pill_patch_bg": "rgba(17, 210, 242, 0.16)",
    "pill_patch_border": "rgba(59, 219, 246, 0.42)",
    "pill_patch_text": "#6eeeff",
    "status_ok_bg": "rgba(16, 185, 129, 0.18)",
    "status_ok_text": "#6ee7b7",
    "status_ok_border": "rgba(52, 211, 153, 0.42)",
    "status_err_bg": "rgba(232, 48, 97, 0.20)",
    "status_err_text": "#ff8cad",
    "status_err_border": "rgba(232, 48, 97, 0.48)",
    "status_cancel_bg": "rgba(245, 158, 11, 0.18)",
    "status_cancel_text": "#fcd34d",
    "status_cancel_border": "rgba(251, 191, 36, 0.42)",
    "switch_track_off": "rgba(255, 255, 255, 0.16)",
    "switch_track_on": "#685bd9",
    "switch_thumb": "#ffffff",
}


def get_theme_tokens(theme: str = "light") -> Dict[str, str]:
    """Return the token dictionary for the requested theme ('light' or 'dark')."""
    return DARK_TOKENS if theme == "dark" else LIGHT_TOKENS


def get_theme_qss(theme: str = "light") -> str:
    """Build the complete Apple Liquid Glass QSS stylesheet for 'light' or 'dark'."""
    t = get_theme_tokens(theme)
    return f"""
QMainWindow {{
    background-color: {t["surface"]};
    color: {t["text_primary"]};
    font-family: {FONT_STACK_SANS};
    font-size: 13px;
}}

QWidget {{
    color: {t["text_primary"]};
    font-family: {FONT_STACK_SANS};
    font-size: 13px;
}}

QWidget#TransparentContainer, QWidget#GlassPage, QStackedWidget#GlassStack {{
    background-color: transparent;
}}

QFrame#Sidebar {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_sidebar_top"]},
        stop:1 {t["glass_sidebar_bot"]}
    );
    border: none;
    border-right: 1px solid {t["sidebar_border"]};
}}

QFrame#TopBar {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_topbar_top"]},
        stop:1 {t["glass_topbar_bot"]}
    );
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
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["glass_rim_right"]};
    border-bottom: 1px solid {t["glass_rim_bot"]};
    border-radius: 14px;
}}

QFrame#HeroCard, QFrame#UpdatesListCard {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_hero_top"]},
        stop:0.45 {t["glass_hero_mid"]},
        stop:1 {t["glass_hero_bot"]}
    );
    border-radius: 20px;
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["glass_rim_right"]};
    border-bottom: 1px solid {t["glass_rim_bot"]};
}}

QFrame#Card {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_card_top"]},
        stop:1 {t["glass_card_bot"]}
    );
    border-radius: 16px;
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["glass_rim_right"]};
    border-bottom: 1px solid {t["glass_rim_bot"]};
}}

QFrame#Card:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_card_hover_top"]},
        stop:1 {t["glass_card_hover_bot"]}
    );
    border: 1px solid {t["card_hover_border"]};
}}

QFrame#ProgressBanner {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_hero_top"]},
        stop:1 {t["banner_bg"]}
    );
    border-radius: 18px;
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["banner_border"]};
    border-bottom: 1px solid {t["banner_border"]};
}}

QFrame#NotificationsPopover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_popover_top"]},
        stop:1 {t["glass_popover_bot"]}
    );
    border-radius: 18px;
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["glass_rim_right"]};
    border-bottom: 1px solid {t["glass_rim_bot"]};
}}

QFrame#NotificationRow {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {t["glass_card_top"]},
        stop:1 {t["glass_card_bot"]}
    );
    border-radius: 12px;
    border: 1px solid {t["card_border"]};
}}

QFrame#NotificationRow[level="success"] {{
    border-left: 3px solid {t["toast_success_icon_bg"]};
}}

QFrame#NotificationRow[level="warning"] {{
    border-left: 3px solid {t["toast_warning_icon_bg"]};
}}

QPushButton#GhostLinkButton {{
    background-color: transparent;
    border: none;
    border-radius: 9px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    color: {t["text_muted"]};
}}

QPushButton#GhostLinkButton:hover {{
    background-color: {t["secondary_bg"]};
    color: {t["text_primary"]};
}}

QPushButton#ExpandButton {{
    background-color: {t["secondary_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["secondary_border"]};
    border-bottom: 1px solid {t["secondary_border"]};
    border-radius: 12px;
    padding: 6px;
    color: {t["text_primary"]};
}}

QPushButton#ExpandButton:hover {{
    background-color: {t["secondary_hover"]};
    border: 1px solid {t["card_hover_border"]};
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
    border-radius: 8px;
    padding: 2px 9px;
}}

QLabel#PercentBadge {{
    font-family: {FONT_STACK_MONO};
    font-size: 12px;
    font-weight: 700;
    color: {t["mono_text"]};
    background-color: {t["mono_bg"]};
    border: 1px solid {t["mono_border"]};
    border-radius: 8px;
    padding: 2px 9px;
}}

QLabel#StatChip {{
    font-family: {FONT_STACK_SANS};
    font-size: 12px;
    font-weight: 600;
    color: {t["chip_text"]};
    background-color: {t["chip_bg"]};
    border-top: 1px solid {t["chip_border"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["chip_border_bot"]};
    border-bottom: 1px solid {t["chip_border_bot"]};
    border-radius: 12px;
    padding: 4px 12px;
}}

QLabel#CategoryPill {{
    font-family: {FONT_STACK_SANS};
    font-size: 11px;
    font-weight: 700;
    border-radius: 10px;
    padding: 2px 10px;
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
    border-radius: 11px;
    padding: 4px 12px;
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
    background-color: {t["secondary_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["secondary_border"]};
    border-bottom: 1px solid {t["secondary_border"]};
    border-radius: 12px;
    padding: 6px;
    color: {t["text_primary"]};
}}

QPushButton#IconButton:hover {{
    background-color: {t["secondary_hover"]};
    border: 1px solid {t["card_hover_border"]};
}}

QPushButton#NavButton {{
    text-align: left;
    padding: 10px 14px;
    border-radius: 12px;
    border: 1px solid transparent;
    background-color: transparent;
    color: {t["nav_text"]};
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#NavButton:hover {{
    background-color: {t["nav_hover_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    color: {t["nav_hover_text"]};
}}

QPushButton#NavButton[active="true"] {{
    background-color: {t["nav_active_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["nav_active_border"]};
    border-right: 1px solid {t["nav_active_border"]};
    border-bottom: 1px solid {t["nav_active_border"]};
    color: {t["nav_active_text"]};
    font-weight: 700;
}}

QPushButton#PrimaryButton {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary"]},
        stop:1 {t["primary_end"]}
    );
    color: {t["on_primary"]};
    border-top: 1px solid rgba(255, 255, 255, 0.42);
    border-left: 1px solid rgba(255, 255, 255, 0.22);
    border-right: 1px solid rgba(0, 0, 0, 0.08);
    border-bottom: 1px solid rgba(0, 0, 0, 0.14);
    border-radius: 12px;
    padding: 9px 18px;
    font-weight: 700;
}}

QPushButton#PrimaryButton:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {t["primary_hover"]},
        stop:1 {t["primary_hover_end"]}
    );
}}

QPushButton#PrimaryButton:disabled {{
    background: {t["disabled_bg"]};
    border: 1px solid transparent;
    color: {t["disabled_text"]};
}}

QPushButton#SecondaryButton {{
    background-color: {t["secondary_bg"]};
    color: {t["secondary_text"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["secondary_border"]};
    border-bottom: 1px solid {t["secondary_border"]};
    border-radius: 12px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton#SecondaryButton:hover {{
    background-color: {t["secondary_hover"]};
    border: 1px solid {t["card_hover_border"]};
}}

QPushButton#SecondaryButton:disabled {{
    background-color: {t["disabled_bg"]};
    border: 1px solid transparent;
    color: {t["disabled_text"]};
}}

QPushButton#CompactButton {{
    background-color: {t["secondary_bg"]};
    color: {t["secondary_text"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["secondary_border"]};
    border-bottom: 1px solid {t["secondary_border"]};
    border-radius: 10px;
    padding: 5px 13px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#CompactButton:hover {{
    background-color: {t["secondary_hover"]};
    border: 1px solid {t["card_hover_border"]};
}}

QPushButton#CompactButton:disabled {{
    background-color: {t["disabled_bg"]};
    border: 1px solid transparent;
    color: {t["disabled_text"]};
}}

QLineEdit#SearchInput {{
    background-color: {t["input_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["input_border"]};
    border-right: 1px solid {t["input_border"]};
    border-bottom: 1px solid {t["input_border"]};
    border-radius: 12px;
    padding: 8px 14px;
    color: {t["text_primary"]};
    selection-background-color: {t["primary"]};
    selection-color: {t["on_primary"]};
}}

QLineEdit#SearchInput:focus {{
    background-color: {t["input_focus_bg"]};
    border: 1.5px solid {t["card_hover_border"]};
}}

QCheckBox {{
    spacing: 8px;
    background: transparent;
}}

QProgressBar#DownloadBar {{
    background-color: {t["bar_bg"]};
    border: 1px solid {t["glass_rim_left"]};
    border-radius: 6px;
    height: 11px;
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
    border-radius: 16px;
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["glass_rim_left"]};
    border-right: 1px solid {t["card_border"]};
    border-bottom: 1px solid {t["card_border"]};
    background-color: {t["glass_popover_top"]};
}}

QFrame#StatusToast[level="success"] {{
    background-color: {t["toast_success_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["toast_success_border"]};
    border-right: 1px solid {t["toast_success_border"]};
    border-bottom: 1px solid {t["toast_success_border"]};
}}

QFrame#StatusToast[level="warning"] {{
    background-color: {t["toast_warning_bg"]};
    border-top: 1px solid {t["glass_rim_top"]};
    border-left: 1px solid {t["toast_warning_border"]};
    border-right: 1px solid {t["toast_warning_border"]};
    border-bottom: 1px solid {t["toast_warning_border"]};
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
