const { test } = require('node:test');
const assert = require('node:assert/strict');
const api = require('../src/main.js');

function signal() {
    const handlers = [];
    return { connect(fn) { handlers.push(fn); }, emit(...args) { handlers.forEach(fn => fn(...args)); } };
}

function desktop({ plasma5 = false, config = {}, app = true } = {}) {
    const screens = [
        { name: 'wide', geometry: { x: -1920, y: 300, width: 1920, height: 1080 }, area: { x: -1920, y: 340, width: 1920, height: 1040 } },
        { name: 'portrait', geometry: { x: 0, y: 0, width: 1080, height: 1920 }, area: { x: 0, y: 0, width: 1080, height: 1880 } }
    ];
    const timers = [], updates = [], outlines = [];
    const work = { internalId: 'work', managed: true, normalWindow: true, resourceClass: 'editor',
        moveable: true, resizeable: true, moveableAcrossScreens: true, maximizable: true, maximizeMode: 0,
        output: screens[0], screen: 0, frameGeometry: { x: -1700, y: 500, width: 640, height: 480 },
        frameGeometryChanged: signal(),
        setMaximize(v, h) { this.maximizeMode = Number(v) + 2 * Number(h); } };
    const started = signal(), stepped = signal(), finished = signal();
    Object.assign(work, plasma5 ? { clientStartUserMovedResized: started, clientStepUserMovedResized: stepped, clientFinishUserMovedResized: finished } :
        { interactiveMoveResizeStarted: started, interactiveMoveResizeStepped: stepped, interactiveMoveResizeFinished: finished });
    const ws = { screens: plasma5 ? undefined : screens, numScreens: 2, currentDesktop: 1,
        stackingOrder: [work], clientList: () => ws.stackingOrder, activeWindow: work, activeClient: work,
        cursorPos: { x: -1400, y: 510 }, cursorPosChanged: signal(), windowAdded: signal(), windowRemoved: signal(),
        currentDesktopChanged: signal(), screensChanged: signal(),
        clientArea(kind, output) { return { ...(typeof output === 'number' ? screens[output] : output)[kind === 1 ? 'geometry' : 'area'] }; },
        sendClientToScreen(w, output) { w.output = typeof output === 'number' ? screens[output] : output; w.screen = screens.indexOf(w.output); },
        showOutline(x, y, width, height) { outlines.push({ x, y, width, height }); }, hideOutline() { outlines.push(null); } };
    let overlay;
    const controller = api.start({ workspace: ws, KWin: { MaximizeArea: 0, ScreenArea: 1 },
        readConfig: (k, fallback) => k in config ? config[k] : fallback,
        registerShortcut() {},
        createTimer() {
            const timer = { timeout: signal(), running: false, start() { this.running = true; }, stop() { this.running = false; } };
            timers.push(timer); return timer;
        },
        callDBus(service, path, iface, method, raw) {
            if (method !== 'SnapUpdate') return;
            const model = JSON.parse(raw); updates.push(model);
            if (model.visible && app && !overlay) {
                overlay = { internalId: 'overlay', resourceClass: 'krect', caption: 'KRect Snap Bar',
                    frameGeometry: { x: 0, y: 0, width: 648, height: 120 } };
                ws.windowAdded.emit(overlay);
            }
        } });
    function pointer(x, y) { ws.cursorPos = { x, y }; ws.cursorPosChanged.emit(); }
    function begin() { work.move = true; started.emit(work); }
    function move(x, y) {
        work.frameGeometry = { ...work.frameGeometry, x: x - 150, y: y - 15 };
        pointer(x, y); stepped.emit(work, work.frameGeometry);
    }
    function open(screen = screens[0]) {
        move(screen.area.x + screen.area.width / 2, screen.area.y + 10);
        timers[0].timeout.emit();
        return updates.at(-1);
    }
    function hover(action, screen = screens[0]) {
        const model = open(screen), cell = model.cells.find(c => c.action === action).rect;
        move(model.geometry.x + cell.x + cell.width / 2, model.geometry.y + cell.y + cell.height / 2);
    }
    function finish(cancel = false, beforeFlush) {
        work.move = false;
        finished.emit(work);
        // The finish signal precedes KWin's blocked geometry commit.
        if (cancel) work.frameGeometry = { ...initial };
        if (beforeFlush) beforeFlush();
        if (timers[1].running) timers[1].timeout.emit();
    }
    const initial = { ...work.frameGeometry };
    return { ws, work, controller, screens, timers, updates, outlines, initial, pointer, begin, move, open, hover, finish, config };
}

for (const plasma5 of [false, true]) {
    test(`Plasma ${plasma5 ? 5 : 6}: top drag shows layouts, previews a region, drops once, and restores`, () => {
        const h = desktop({ plasma5 }); h.begin(); h.hover('left');
        const target = api.zone(h.screens[0].area, [0, 0, .5, 1], 8);
        assert.deepEqual(h.outlines.at(-1), target);
        assert.notDeepEqual(h.work.frameGeometry, target, 'hover does not place the window');
        h.finish();
        assert.deepEqual(h.work.frameGeometry, target);
        assert.equal(h.updates.at(-1).visible, false);
        assert.equal(h.controller.execute('restore'), true);
        assert.deepEqual(h.work.frameGeometry, h.initial);
    });

    test(`Plasma ${plasma5 ? 5 : 6}: Esc restored after Finished does not snap`, () => {
        const h = desktop({ plasma5 }); h.begin(); h.hover('right'); h.finish(true);
        assert.deepEqual(h.work.frameGeometry, h.initial);
        assert.equal(h.controller.execute('restore'), false);
    });
}

test('a hidden or absent app cannot produce an invisible snap target', () => {
    const h = desktop({ app: false }); h.begin(); h.hover('left');
    const dragged = { ...h.work.frameGeometry }; h.finish();
    assert.deepEqual(h.work.frameGeometry, dragged);
    assert.deepEqual(h.outlines, []);
});

test('leaving the strip, its gaps, or releasing before entering a cell preserves normal dragging', () => {
    for (const where of ['away', 'gap', 'top']) {
        const h = desktop(); h.begin(); h.hover('left');
        const g = h.updates.at(-1).geometry;
        if (where === 'away') h.move(g.x, g.y + g.height + 80);
        if (where === 'gap') h.move(g.x + 2, g.y + 40);
        if (where === 'top') h.move(g.x + g.width / 2, g.y);
        const dragged = { ...h.work.frameGeometry }; h.finish();
        assert.deepEqual(h.work.frameGeometry, dragged);
    }
});

test('normal screen edges outside the center activation area remain untouched', () => {
    const h = desktop(); h.begin(); h.move(-1920, 340); h.finish();
    assert.equal(h.updates.length, 0);
    assert.deepEqual(h.outlines, []);
});

test('a top panel does not prevent activation at the physical screen edge', () => {
    const h = desktop(); h.begin(); h.move(-960, 300);
    assert.equal(h.updates.at(-1).visible, true);
    assert.ok(h.updates.at(-1).geometry.y > h.screens[0].area.y);
});

test('Esc restoring native maximization or a tile rejects even an unacknowledged Wayland frame', () => {
    for (const restored of [{ maximizeMode: 3 }, { tile: {} }]) {
        const h = desktop(); h.begin(); h.hover('right');
        const lastAcknowledged = { ...h.work.frameGeometry };
        h.finish(false, () => Object.assign(h.work, restored));
        assert.deepEqual(h.work.frameGeometry, lastAcknowledged);
        assert.equal(h.controller.execute('restore'), false);
    }
});

test('portrait display under the pointer supplies the work area and vertical thirds', () => {
    const h = desktop(); h.begin(); h.hover('center-third', h.screens[1]); h.finish();
    assert.equal(h.work.output, h.screens[1]);
    assert.deepEqual(h.work.frameGeometry, api.zone(h.screens[1].area, [0, 1 / 3, 1, 1 / 3], 8));
    h.controller.execute('restore');
    assert.equal(h.work.output, h.screens[0]);
    assert.deepEqual(h.work.frameGeometry, h.initial);
});

test('disabled snap bar, excluded/fixed/fullscreen windows and resize gestures never open it', () => {
    for (const override of [{ resize: true }, { fullScreen: true }, { resizeable: false }, { resourceClass: 'krect' }, { resourceClass: 'ignored' }]) {
        const h = desktop({ config: { IgnoredApplications: 'ignored' } }); Object.assign(h.work, override);
        h.begin(); h.move(-960, 350);
        assert.equal(h.updates.length, 0);
    }
    const h = desktop({ config: { SnapBar: 'false' } }); h.begin(); h.move(-960, 350);
    assert.equal(h.updates.length, 0);
});

test('desktop changes, output removal and target closure cancel pending drops', () => {
    for (const invalidate of [h => h.ws.currentDesktopChanged.emit(), h => h.ws.screensChanged.emit(), h => h.ws.windowRemoved.emit(h.work)]) {
        const h = desktop(); h.begin(); h.hover('left');
        const dragged = { ...h.work.frameGeometry };
        h.finish(false, () => invalidate(h));
        assert.deepEqual(h.work.frameGeometry, dragged);
    }
});

test('changed work area or disabled preference before deferred drop rejects stale placement', () => {
    for (const change of [h => { h.screens[0].area.y += 10; }, h => { h.config.SnapBar = false; }]) {
        const h = desktop(); h.begin(); h.hover('left');
        const dragged = { ...h.work.frameGeometry };
        h.finish(false, () => change(h));
        assert.deepEqual(h.work.frameGeometry, dragged);
    }
});

test('small displays do not render unusable layouts; fractional and negative coordinates stay bounded', () => {
    assert.equal(api.snapLayout({ x: 0, y: 0, width: 300, height: 200 }, false), null);
    const area = { x: -1536.5, y: 22.5, width: 1536.5, height: 831.5 };
    const layout = api.snapLayout(area, false);
    assert.ok(layout.geometry.x >= area.x);
    assert.ok(layout.geometry.x + layout.geometry.width <= area.x + area.width);
    for (const cell of layout.cells) {
        assert.ok(cell.rect.width > 0 && cell.rect.height > 0);
        assert.ok(cell.rect.x + cell.rect.width <= layout.geometry.width);
        assert.ok(cell.rect.y + cell.rect.height <= layout.geometry.height);
    }
});
