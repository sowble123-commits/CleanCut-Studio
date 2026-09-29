# config.py
"""
프로젝트 전역에서 공통으로 사용되는 색상, 폰트 및 설정 변수를 관리합니다.
"""

SETTINGS_FILE = "settings.json"

# 다크/화이트 모드 모두 대응하는 튜플 컬러 팔레트 (Light, Dark)
BG_MAIN = ("#F3F4F6", "#0B0C10")
BG_SIDEBAR = ("#FFFFFF", "#11131A")
BG_CARD = ("#FFFFFF", "#161922")
BG_INNER = ("#F1F5F9", "#0F1117")
BORDER_COLOR = ("#E2E8F0", "#262936")

ACCENT = "#5E6AD2"
ACCENT_HOVER = "#4E5AC0"

TEXT_MAIN = ("#111827", "#F3F4F6")
TEXT_SUB = ("#64748B", "#8A8F98")

ERROR_COLOR = "#EF4444"
SUCCESS_COLOR = "#10B981"
WARN_COLOR = "#F59E0B"

# 공통으로 사용될 폰트 설정 (이름, 크기, 굵기)
FONT_MAIN_TITLE = ("맑은 고딕", 20, "bold")
FONT_CARD_TITLE = ("맑은 고딕", 14, "bold")
FONT_DEFAULT = ("맑은 고딕", 12)
FONT_DEFAULT_BOLD = ("맑은 고딕", 12, "bold")
FONT_SMALL = ("맑은 고딕", 11)
FONT_SMALL_BOLD = ("맑은 고딕", 11, "bold")