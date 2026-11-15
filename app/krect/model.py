"""Action vocabulary shared by the desktop window and tray."""
from .qt import QtCore

KOREAN = QtCore.QLocale.system().name().startswith("ko")


def tr(english, korean):
    return korean if KOREAN else english


ACTIONS = [
    ("left", "Left half", "왼쪽 절반"), ("right", "Right half", "오른쪽 절반"),
    ("top", "Top half", "위쪽 절반"), ("bottom", "Bottom half", "아래쪽 절반"),
    ("top-left", "Top left", "왼쪽 위"), ("top-right", "Top right", "오른쪽 위"),
    ("bottom-left", "Bottom left", "왼쪽 아래"), ("bottom-right", "Bottom right", "오른쪽 아래"),
    ("first-third", "First third", "첫 번째 ⅓"), ("center-third", "Center third", "가운데 ⅓"),
    ("last-third", "Last third", "마지막 ⅓"), ("first-two-thirds", "First two thirds", "앞쪽 ⅔"),
    ("last-two-thirds", "Last two thirds", "뒤쪽 ⅔"),
    ("center", "Center", "가운데로"), ("maximize", "Maximize", "최대화"),
    ("restore", "Restore", "원래 배치로"),
    ("previous-screen", "Previous display", "이전 화면"), ("next-screen", "Next display", "다음 화면"),
    ("swap", "Swap windows…", "두 창 교환…"), ("undo-swap", "Undo swap", "교환 되돌리기"),
]
LABELS = {key: tr(en, ko) for key, en, ko in ACTIONS}


def fraction(action, portrait=False):
    zones = {
        "left": (0, 0, .5, 1), "right": (.5, 0, .5, 1),
        "top": (0, 0, 1, .5), "bottom": (0, .5, 1, .5),
        "top-left": (0, 0, .5, .5), "top-right": (.5, 0, .5, .5),
        "bottom-left": (0, .5, .5, .5), "bottom-right": (.5, .5, .5, .5),
        "first-third": (0, 0, 1/3, 1), "center-third": (1/3, 0, 1/3, 1),
        "last-third": (2/3, 0, 1/3, 1), "first-two-thirds": (0, 0, 2/3, 1),
        "last-two-thirds": (1/3, 0, 2/3, 1), "maximize": (0, 0, 1, 1),
        "center": (.2, .2, .6, .6), "restore": (.1, .15, .65, .65),
    }
    f = zones.get(action)
    return (f[1], f[0], f[3], f[2]) if f and portrait and "third" in action else f
