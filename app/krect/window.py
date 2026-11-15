"""Theme-respecting Qt window and native tray menu."""
from . import VERSION
from .about import AboutDialog
from .workspace_page import WorkspacePage
from .model import ACTIONS, LABELS, fraction, tr
from .qt import Action, QtCore as C, QtGui as G, QtWidgets as W, QT_MAJOR, Signal


def text_label(text, wrap=False):
    label = W.QLabel(text)
    label.setTextFormat(C.Qt.TextFormat.PlainText)
    label.setWordWrap(wrap)
    return label


def heading(text):
    label = text_label(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


def draw_layout(painter, bounds, action, palette, portrait=False):
    painter.setRenderHint(G.QPainter.RenderHint.Antialiasing)
    outline = palette.color(G.QPalette.ColorRole.WindowText)
    painter.setPen(G.QPen(outline, 1.5))
    painter.setBrush(C.Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(bounds, 2, 2)
    f = fraction(action, portrait)
    if f:
        inner = bounds.adjusted(3, 3, -3, -3)
        painter.setPen(C.Qt.PenStyle.NoPen)
        painter.setBrush(palette.color(G.QPalette.ColorRole.Highlight))
        painter.drawRect(C.QRectF(inner.x() + inner.width()*f[0], inner.y() + inner.height()*f[1],
                                 inner.width()*f[2], inner.height()*f[3]))
    elif action == "swap":
        center = bounds.center()
        for sign in (-1, 1):
            y = center.y() - sign * 5
            painter.drawLine(C.QPointF(center.x()-9*sign, y), C.QPointF(center.x()+9*sign, y))
            painter.drawLine(C.QPointF(center.x()+9*sign, y), C.QPointF(center.x()+4*sign, y-4))
            painter.drawLine(C.QPointF(center.x()+9*sign, y), C.QPointF(center.x()+4*sign, y+4))
    else:
        center = bounds.center()
        sign = 1 if action == "next-screen" else -1
        painter.drawLine(C.QPointF(center.x()-7*sign, center.y()), C.QPointF(center.x()+7*sign, center.y()))
        painter.drawLine(C.QPointF(center.x()+7*sign, center.y()), C.QPointF(center.x()+2*sign, center.y()-5))
        painter.drawLine(C.QPointF(center.x()+7*sign, center.y()), C.QPointF(center.x()+2*sign, center.y()+5))


def layout_icon(action, palette, portrait=False):
    if action == "undo-swap":
        themed = G.QIcon.fromTheme("edit-undo")
        if not themed.isNull():
            return themed
    pixmap = G.QPixmap(80, 64)
    pixmap.fill(C.Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(2)
    painter = G.QPainter(pixmap)
    draw_layout(painter, C.QRectF(2, 2, 36, 28), action, palette, portrait)
    painter.end()
    return G.QIcon(pixmap)


class LayoutButton(W.QToolButton):
    preview = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.setToolButtonStyle(C.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIconSize(C.QSize(40, 32))
        self.setMinimumSize(122, 78)
        self.setSizePolicy(W.QSizePolicy.Policy.Expanding, W.QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(C.Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(LABELS[action])

    def enterEvent(self, event):
        self.preview.emit(self.action)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.preview.emit("")
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self.preview.emit(self.action)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.preview.emit("")
        super().focusOutEvent(event)


class DisplayPreview(W.QWidget):
    def __init__(self):
        super().__init__()
        self.status = {}
        self.action = ""
        self.portrait_thirds = True
        self.setFixedHeight(132)
        self.setAccessibleName(tr("Display arrangement and window placement preview", "모니터 구성과 창 배치 미리보기"))

    def preview(self, action):
        self.action = action
        self.update()

    def paintEvent(self, event):
        painter = G.QPainter(self)
        painter.setRenderHint(G.QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        painter.fillRect(self.rect(), palette.brush(G.QPalette.ColorRole.Base))
        screens = self.status.get("screens", [])
        if not screens:
            painter.setPen(palette.color(G.QPalette.ColorRole.Text))
            painter.drawText(self.rect().adjusted(20, 8, -20, -8), C.Qt.AlignmentFlag.AlignCenter | C.Qt.TextFlag.TextWordWrap,
                             tr("Enable KRect to see your displays.", "KRect를 켜면 모니터 구성이 표시돼요."))
            return
        left = min(s["geometry"]["x"] for s in screens)
        top = min(s["geometry"]["y"] for s in screens)
        width = max(s["geometry"]["x"]+s["geometry"]["width"] for s in screens)-left
        height = max(s["geometry"]["y"]+s["geometry"]["height"] for s in screens)-top
        scale = min((self.width()-48)/width, (self.height()-40)/height)
        dx, dy = (self.width()-width*scale)/2, (self.height()-height*scale)/2

        def mapped(r):
            return C.QRectF(dx+(r["x"]-left)*scale, dy+(r["y"]-top)*scale, r["width"]*scale, r["height"]*scale)

        target = self.status.get("target")
        for i, screen in enumerate(screens):
            r = mapped(screen["geometry"])
            selected = target and target["screen"] == screen["name"]
            painter.setPen(G.QPen(palette.color(G.QPalette.ColorRole.Highlight if selected else G.QPalette.ColorRole.Mid), 2 if selected else 1))
            painter.setBrush(palette.brush(G.QPalette.ColorRole.AlternateBase))
            painter.drawRoundedRect(r, 3, 3)
            if selected:
                geometry = target["geometry"]
                area = screen.get("area") or screen["geometry"]
                f = fraction(self.action, self.portrait_thirds and area["height"] > area["width"])
                if f:
                    geometry = dict(x=area["x"]+area["width"]*f[0], y=area["y"]+area["height"]*f[1], width=area["width"]*f[2], height=area["height"]*f[3])
                fill = palette.color(G.QPalette.ColorRole.Highlight)
                fill.setAlpha(150)
                painter.setBrush(fill)
                painter.setPen(C.Qt.PenStyle.NoPen)
                painter.drawRect(mapped(geometry).intersected(r.adjusted(2, 2, -2, -2)))
            painter.setPen(palette.color(G.QPalette.ColorRole.Text))
            painter.drawText(r.adjusted(4, 4, -4, -4), C.Qt.AlignmentFlag.AlignBottom | C.Qt.AlignmentFlag.AlignHCenter,
                             str(i+1))


class Window(W.QMainWindow):
    def __init__(self, backend, icon):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("KRect")
        self.setWindowIcon(icon)
        self.resize(800, 870)
        self.setMinimumSize(650, 690)
        self.buttons = {}
        self.tray_actions = {}
        self.key_editors = {}
        self.shortcut_values = {}
        self.shortcuts_loaded = False
        self.portrait = None
        self.quitting = False
        self.about_dialog = None
        central = W.QWidget()
        self.setCentralWidget(central)
        outer = W.QVBoxLayout(central)
        outer.setContentsMargins(20, 16, 20, 12)
        outer.setSpacing(12)
        header = W.QHBoxLayout()
        logo = W.QLabel()
        logo.setPixmap(icon.pixmap(40, 40))
        header.addWidget(logo)
        title = W.QVBoxLayout()
        name = heading("KRect")
        font = name.font()
        font.setPointSizeF(font.pointSizeF()*1.4)
        name.setFont(font)
        title.addWidget(name)
        title.addWidget(text_label(tr("A place for every window.", "모든 창을 원하는 자리에.")))
        header.addLayout(title)
        header.addStretch()
        self.enable = W.QPushButton()
        self.enable.setCheckable(True)
        self.enable.clicked.connect(self.toggle)
        header.addWidget(self.enable)
        outer.addLayout(header)
        self.tabs = W.QTabWidget()
        self.tabs.addTab(self.layouts_tab(), tr("Layouts", "창 배치"))
        self.tabs.addTab(self.shortcuts_tab(), tr("Shortcuts", "단축키"))
        self.tabs.addTab(self.preferences_tab(), tr("Preferences", "환경설정"))
        self.workspace_page = WorkspacePage(backend)
        self.tabs.addTab(self.workspace_page, tr("Workspaces", "작업 공간"))
        self.tabs.currentChanged.connect(self.tab_changed)
        outer.addWidget(self.tabs, 1)
        self.feedback = text_label("", True)
        self.feedback.setMinimumHeight(self.fontMetrics().height()*2)
        self.feedback.setAccessibleName(tr("Status", "상태"))
        outer.addWidget(self.feedback)
        footer = W.QHBoxLayout()
        footer.addWidget(text_label(f"KRect {VERSION} · Plasma {backend.major} · " +
                                    ("Wayland" if G.QGuiApplication.platformName().startswith("wayland") else "X11")))
        footer.addStretch()
        self.about_button = W.QPushButton(tr("About", "앱 정보"))
        self.about_button.clicked.connect(self.show_about)
        footer.addWidget(self.about_button)
        quit_button = W.QPushButton(tr("Quit", "종료"))
        quit_button.clicked.connect(self.quit)
        footer.addWidget(quit_button)
        outer.addLayout(footer)
        self.create_tray(icon)
        backend.changed.connect(self.update_status)
        backend.message.connect(self.show_message)
        self.update_status({})

    def layouts_tab(self):
        page = W.QWidget()
        box = W.QVBoxLayout(page)
        box.setSizeConstraint(W.QLayout.SizeConstraint.SetMinimumSize)
        box.setContentsMargins(16, 16, 16, 12)
        box.setSpacing(10)
        box.addWidget(heading(tr("Selected window", "배치할 창")))
        self.target = text_label("")
        self.target.setMinimumWidth(0)
        box.addWidget(self.target)
        self.display_info = text_label("", True)
        box.addWidget(self.display_info)
        self.preview = DisplayPreview()
        box.addWidget(self.preview)
        grid = W.QGridLayout()
        grid.setSpacing(6)
        for i, (action, _, _) in enumerate(ACTIONS[:16]):
            button = LayoutButton(action)
            button.clicked.connect(lambda checked=False, a=action: self.backend.apply(a))
            button.preview.connect(self.preview.preview)
            self.buttons[action] = button
            grid.addWidget(button, i//4, i%4)
        box.addLayout(grid)
        utilities = W.QGridLayout()
        for i, (action, _, _) in enumerate(ACTIONS[16:]):
            button = W.QPushButton(LABELS[action])
            button.clicked.connect(lambda checked=False, a=action: self.backend.apply(a))
            self.buttons[action] = button
            utilities.addWidget(button, i // 2, i % 2)
        box.addLayout(utilities)
        box.addWidget(text_label(tr("Select a work window, then choose a layout here or from the tray. Repeat a half shortcut to cycle ½ → ⅔ → ⅓.",
                                    "작업할 창을 선택한 다음 여기나 트레이에서 배치하세요. 절반 단축키를 연속으로 누르면 ½ → ⅔ → ⅓로 바뀌어요."), True))
        scroll = W.QScrollArea()
        scroll.setFrameShape(W.QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def shortcuts_tab(self):
        page = W.QWidget()
        box = W.QVBoxLayout(page)
        box.setContentsMargins(16, 16, 16, 12)
        box.addWidget(text_label(tr("Click a shortcut and press a new key combination. Use the clear button to remove it. Conflicts are checked before saving.",
                                    "단축키를 클릭하고 새 조합을 누르세요. 지우기 버튼으로 삭제할 수 있어요. 저장 전에 충돌을 확인해요."), True))
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        content = W.QWidget()
        form = W.QFormLayout(content)
        form.setSpacing(10)
        for action, _, _ in ACTIONS:
            row = W.QHBoxLayout()
            editor = W.QKeySequenceEdit()
            editor.setAccessibleName(LABELS[action])
            self.key_editors[action] = editor
            row.addWidget(editor, 1)
            clear = W.QToolButton()
            clear.setIcon(G.QIcon.fromTheme("edit-clear"))
            clear.setToolTip(tr("Clear shortcut", "단축키 지우기"))
            clear.setAccessibleName(tr("Clear ", "지우기: ") + LABELS[action])
            clear.clicked.connect(editor.clear)
            row.addWidget(clear)
            form.addRow(LABELS[action], row)
        scroll.setWidget(content)
        box.addWidget(scroll, 1)
        row = W.QHBoxLayout()
        kde = W.QPushButton(tr("KDE shortcuts…", "KDE 단축키…"))
        kde.clicked.connect(lambda: self.perform(self.backend.open_kde_shortcuts))
        row.addWidget(kde)
        reload_button = W.QPushButton(tr("Reload", "다시 불러오기"))
        reload_button.clicked.connect(self.load_shortcuts)
        row.addWidget(reload_button)
        row.addStretch()
        self.save_keys = W.QPushButton(tr("Save shortcuts", "단축키 저장"))
        self.save_keys.clicked.connect(self.save_shortcuts)
        row.addWidget(self.save_keys)
        box.addLayout(row)
        return page

    def preferences_tab(self):
        page = W.QWidget()
        box = W.QVBoxLayout(page)
        box.setContentsMargins(20, 20, 20, 16)
        box.setSizeConstraint(W.QLayout.SizeConstraint.SetMinimumSize)
        box.setSpacing(16)
        box.addWidget(heading(tr("Window placement", "창 배치")))
        form = W.QFormLayout()
        form.setSpacing(14)
        values = self.backend.values
        self.gap = W.QSpinBox()
        self.gap.setRange(0, 64)
        self.gap.setSuffix(tr(" logical px", " 논리 픽셀"))
        self.gap.setValue(values["Gap"])
        form.addRow(tr("Window gap", "창 사이 간격"), self.gap)
        self.cycle = W.QCheckBox(tr("Cycle half → two thirds → third", "절반 → ⅔ → ⅓ 순환"))
        self.cycle.setChecked(values["CycleHalves"])
        form.addRow(self.cycle)
        self.cycle_timeout = W.QSpinBox()
        self.cycle_timeout.setRange(200, 5000)
        self.cycle_timeout.setSuffix(" ms")
        self.cycle_timeout.setValue(values["CycleTimeout"])
        self.cycle_timeout.setEnabled(self.cycle.isChecked())
        self.cycle.toggled.connect(self.cycle_timeout.setEnabled)
        form.addRow(tr("Repeat within", "연속 입력 간격"), self.cycle_timeout)
        self.portrait_thirds = W.QCheckBox(tr("Stack thirds vertically on portrait displays", "세로 모니터에서 3분할을 위아래로 배치"))
        self.portrait_thirds.setChecked(values["PortraitThirds"])
        form.addRow(self.portrait_thirds)
        self.snap_bar = W.QCheckBox(tr("Show snap layouts when dragging to the top", "창을 화면 상단으로 끌면 배치 막대 표시"))
        self.snap_bar.setChecked(values["SnapBar"])
        form.addRow(self.snap_bar)
        self.snap_assist = W.QCheckBox(tr("Suggest a window for the other half after dragging", "반쪽으로 끌어 배치한 뒤 다른 쪽에 놓을 창 추천"))
        self.snap_assist.setChecked(values["SnapAssist"])
        self.snap_assist.setEnabled(self.snap_bar.isChecked())
        self.snap_bar.toggled.connect(self.snap_assist.setEnabled)
        form.addRow(self.snap_assist)
        box.addLayout(form)
        box.addWidget(text_label(tr("Drag a window to the top center of a display, move into a region, then release. Move away to continue dragging, or press Esc to cancel. Keep KRect running in the tray for this feature.",
                                    "창을 화면 상단 중앙으로 끌고, 막대의 원하는 영역에서 놓으세요. 막대를 벗어나면 일반 드래그로 돌아가고 Esc로 취소할 수 있어요. 이 기능은 KRect가 트레이에서 실행 중일 때 작동해요."), True))
        box.addWidget(heading(tr("Excluded applications", "제외할 앱")))
        box.addWidget(text_label(tr("App IDs or window classes, separated by commas or new lines. Fullscreen and fixed-size windows are always skipped.",
                                    "앱 ID나 창 클래스를 쉼표 또는 줄바꿈으로 구분하세요. 전체 화면과 고정 크기 창은 항상 제외돼요."), True))
        self.exclusions = W.QPlainTextEdit(values["IgnoredApplications"])
        self.exclusions.setPlaceholderText("org.kde.konsole, firefox")
        self.exclusions.setAccessibleName(tr("Excluded applications", "제외할 앱"))
        self.exclusions.setMaximumHeight(100)
        box.addWidget(self.exclusions)
        self.exclude_target = W.QPushButton(tr("Exclude selected application", "선택한 앱 제외하기"))
        self.exclude_target.clicked.connect(self.exclude_application)
        box.addWidget(self.exclude_target)
        box.addWidget(heading(tr("Desktop", "데스크톱")))
        self.autostart = W.QCheckBox(tr("Start KRect in the tray when I log in", "로그인 시 트레이에서 시작"))
        self.autostart.setChecked(self.backend.autostart_path().is_file())
        box.addWidget(self.autostart)
        self.close_tray = W.QCheckBox(tr("Keep in the tray when the window closes", "창을 닫아도 트레이에 유지"))
        self.close_tray.setChecked(self.backend.close_to_tray())
        box.addWidget(self.close_tray)
        box.addWidget(text_label(tr("Applying placement preferences clears saved original placements. Keyboard shortcuts work even when this app is closed.",
                                    "배치 환경설정을 적용하면 저장된 원래 배치가 초기화돼요. 앱을 종료해도 단축키는 작동해요."), True))
        box.addStretch()
        save = W.QPushButton(tr("Apply preferences", "환경설정 적용"))
        save.clicked.connect(self.save_preferences)
        box.addWidget(save, 0, C.Qt.AlignmentFlag.AlignRight)
        scroll = W.QScrollArea()
        scroll.setFrameShape(W.QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def create_tray(self, icon):
        self.tray = W.QSystemTrayIcon(icon, self)
        self.tray.setToolTip("KRect")
        menu = W.QMenu(self)
        self.tray_target = menu.addAction(tr("Select a window to arrange", "배치할 창을 선택하세요"))
        self.tray_target.setEnabled(False)
        menu.addSeparator()
        for i, (action, _, _) in enumerate(ACTIONS):
            if i in (4, 8, 13, 16):
                menu.addSeparator()
            item = menu.addAction(LABELS[action])
            item.triggered.connect(lambda checked=False, a=action: self.backend.apply(a))
            self.tray_actions[action] = item
        menu.addSeparator()
        item = menu.addAction(tr("Open KRect…", "KRect 열기…"))
        item.triggered.connect(self.activate)
        self.tray_enable = menu.addAction(tr("Enable KRect", "KRect 켜기"))
        self.tray_enable.setCheckable(True)
        self.tray_enable.triggered.connect(self.toggle)
        self.tray_about = menu.addAction(tr("About KRect…", "KRect 정보…"))
        self.tray_about.triggered.connect(self.show_about)
        menu.addAction(tr("Quit KRect", "KRect 종료"), self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.activate() if reason == W.QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def show_about(self):
        if self.about_dialog is None:
            self.about_dialog = AboutDialog(self)
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def perform(self, function):
        try:
            function()
        except Exception as error:
            self.show_message(str(error), True)
            return False
        return True

    def toggle(self, checked):
        self.perform(self.backend.start if checked else self.backend.stop)
        self.update_status(self.backend.status)

    def update_status(self, status):
        connected = self.backend.enabled and bool(status)
        self.enable.setChecked(self.backend.enabled)
        self.enable.setText(tr("KRect is on", "KRect 켜짐") if self.backend.enabled else tr("Enable KRect", "KRect 켜기"))
        self.tray_enable.setChecked(self.backend.enabled)
        target = status.get("target") if connected else None
        caption = target["caption"] if target else tr("Select a movable work window, then return here.", "이동 가능한 작업 창을 선택한 뒤 돌아오세요.") if connected else tr("Enable KRect to start arranging windows.", "KRect를 켜고 창 배치를 시작하세요.")
        self.target.setText(self.target.fontMetrics().elidedText(caption, C.Qt.TextElideMode.ElideRight, max(200, self.tabs.width()-65)))
        self.target.setToolTip(caption)
        self.tray_target.setText(caption[:80])
        screens = status.get("screens", [])
        area = target.get("area") if target else None
        portrait = bool(area and area["height"] > area["width"] and self.backend.values["PortraitThirds"])
        if area:
            number = next((i+1 for i, s in enumerate(screens) if s["name"] == target["screen"]), 1)
            self.display_info.setText(tr("Display {n} · {w} × {h} work area · {orientation}", "화면 {n} · 작업 영역 {w} × {h} · {orientation}").format(
                n=number, w=area["width"], h=area["height"], orientation=tr("Portrait", "세로") if area["height"] > area["width"] else tr("Landscape", "가로")))
        else:
            self.display_info.setText(tr("Waiting for KWin…", "KWin 연결 중…") if self.backend.enabled and not connected else " ")
        if self.portrait != portrait:
            self.portrait = portrait
            for action, button in self.buttons.items():
                icon = layout_icon(action, self.palette(), portrait)
                button.setIcon(icon)
                self.tray_actions[action].setIcon(icon)
                button.setText(LABELS[action])
        available = bool(target) and not self.backend.pending
        for action, button in self.buttons.items():
            enabled = available
            if action == "restore":
                enabled = enabled and target.get("canRestore", False)
            elif action == "maximize":
                enabled = enabled and target.get("maximizable", False)
            elif action == "swap":
                enabled = enabled and target.get("canSwap", False)
            elif action == "undo-swap":
                enabled = enabled and target.get("canUndoSwap", False)
            elif action.endswith("-screen"):
                enabled = enabled and len(screens) > 1 and target.get("movableAcrossScreens", False)
            button.setEnabled(bool(enabled))
            self.tray_actions[action].setEnabled(bool(enabled))
        self.save_keys.setEnabled(connected)
        self.exclude_target.setEnabled(bool(target))
        self.preview.status = status if connected else {}
        self.preview.portrait_thirds = self.backend.values["PortraitThirds"]
        self.preview.update()
        if connected and not self.shortcuts_loaded:
            self.load_shortcuts()

    def load_shortcuts(self):
        if not self.backend.enabled:
            return
        def load():
            self.shortcut_values = self.backend.shortcuts()
            for action, editor in self.key_editors.items():
                keys = self.shortcut_values[action]
                editor.setKeySequence(G.QKeySequence(keys[0]) if keys else G.QKeySequence())
                sequence = G.QKeySequence(keys[0]).toString(G.QKeySequence.SequenceFormat.NativeText) if keys else tr("Unassigned", "미지정")
                self.buttons[action].setToolTip(LABELS[action] + " · " + sequence)
                self.tray_actions[action].setText(LABELS[action] + "\t" + sequence)
            self.shortcuts_loaded = True
        self.perform(load)

    def tab_changed(self, index):
        self.feedback.clear()
        if index == 1 and not self.shortcuts_loaded:
            self.load_shortcuts()

    def save_shortcuts(self):
        def save():
            mapping = {}
            for action, editor in self.key_editors.items():
                sequence = editor.keySequence()
                if sequence.count() > 1:
                    raise RuntimeError(tr("Use one key combination per action.", "동작마다 하나의 키 조합을 사용하세요."))
                key = sequence[0].toCombined() if QT_MAJOR == 6 and not sequence.isEmpty() else sequence[0] if not sequence.isEmpty() else 0
                # Preserve alternate bindings when an action was left untouched.
                before = self.shortcut_values.get(action, [])
                mapping[action] = before if before and key == before[0] else [key] if key else []
            self.backend.save_shortcuts(mapping)
            self.load_shortcuts()
        self.perform(save)

    def save_preferences(self):
        values = dict(Gap=self.gap.value(), CycleHalves=self.cycle.isChecked(), CycleTimeout=self.cycle_timeout.value(),
                      PortraitThirds=self.portrait_thirds.isChecked(), SnapBar=self.snap_bar.isChecked(),
                      SnapAssist=self.snap_assist.isChecked(),
                      IgnoredApplications=self.exclusions.toPlainText().strip())
        self.perform(lambda: self.backend.save_settings(values, self.autostart.isChecked(), self.close_tray.isChecked()))

    def exclude_application(self):
        target = self.backend.status.get("target")
        if target and target["application"]:
            text = self.exclusions.toPlainText().strip()
            self.exclusions.setPlainText(text + ("\n" if text else "") + target["application"])

    def show_message(self, text, error=False):
        self.feedback.setText((tr("Could not complete: ", "적용하지 못했어요: ") if error else "") + text)
        self.feedback.setToolTip(text)

    def activate(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.backend.refresh()

    def closeEvent(self, event):
        if not self.quitting and self.backend.close_to_tray() and W.QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
        else:
            self.quit()
            event.accept()

    def quit(self):
        self.quitting = True
        self.tray.hide()
        W.QApplication.instance().quit()
