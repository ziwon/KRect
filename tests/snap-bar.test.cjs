const { test } = require('node:test');
const assert = require('node:assert/strict');
const api = require('../src/main.js');

function signal() {
    const handlers = [];
    return { connect(fn) { handlers.push(fn); }, emit(...args) { handlers.forEach(fn => fn(...args)); } };
}

function desktop({ plasma5 = false, config = {}, app = true, overlayCaption = 'KRect Snap Bar — KRect' } = {}) {
    const screens = [
        { name: 'wide', geometry: { x: -1920, y: 300, width: 1920, height: 1080 }, area: { x: -1920, y: 340, width: 1920, height: 1040 } },
        { name: 'portrait', geometry: { x: 0, y: 0, width: 1080, height: 1920 }, area: { x: 0, y: 0, width: 1080, height: 1880 } }
    ];
    const timers = [], updates = [], outlines = [], assists = [], commands = [], shortcuts = {}, statuses = [];
    let clock = 1000;
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
        currentDesktopChanged: signal(), screensChanged: signal(), windowActivated: signal(),
        clientArea(kind, output) { return { ...(typeof output === 'number' ? screens[output] : output)[kind === 1 ? 'geometry' : 'area'] }; },
        sendClientToScreen(w, output) { w.output = typeof output === 'number' ? screens[output] : output; w.screen = screens.indexOf(w.output); },
        showOutline(x, y, width, height) { outlines.push({ x, y, width, height }); }, hideOutline() { outlines.push(null); } };
    let overlay, chooser;
    const controller = api.start({ workspace: ws, KWin: { MaximizeArea: 0, ScreenArea: 1 },
        now: () => clock,
        readConfig: (k, fallback) => k in config ? config[k] : fallback,
        registerShortcut(id, name, key, fn) { shortcuts[id] = fn; },
        createTimer() {
            const timer = { timeout: signal(), running: false, start() { this.running = true; }, stop() { this.running = false; } };
            timers.push(timer); return timer;
        },
        callDBus(service, path, iface, method, raw) {
            if (method === 'Update') { statuses.push(JSON.parse(raw)); return; }
            if (method === 'TakeCommand') { raw(JSON.stringify(commands.shift() || {})); return; }
            if (method === 'AssistUpdate') {
                const model = JSON.parse(raw); assists.push(model);
                if (model.visible && app && !chooser) {
                    chooser = { internalId: 'chooser', resourceClass: 'krect', caption: 'KRect Fill Space — KRect',
                        frameGeometry: { x: 0, y: 0, width: 400, height: 400 } };
                    ws.windowAdded.emit(chooser);
                }
                return;
            }
            if (method !== 'SnapUpdate') return;
            const model = JSON.parse(raw); updates.push(model);
            if (model.visible && app && !overlay) {
                overlay = { internalId: 'overlay', resourceClass: 'krect', caption: overlayCaption,
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
    function addWindow(id, extra = {}) {
        const w = { ...work, internalId: id, caption: id, resourceClass: id, move: false,
            frameGeometry: { ...initial }, frameGeometryChanged: signal(), ...extra };
        Object.assign(w, plasma5 ? { clientStartUserMovedResized: signal(), clientStepUserMovedResized: signal(), clientFinishUserMovedResized: signal() } :
            { interactiveMoveResizeStarted: signal(), interactiveMoveResizeStepped: signal(), interactiveMoveResizeFinished: signal() });
        ws.stackingOrder.push(w); ws.windowAdded.emit(w); return w;
    }
    function choose(target, session = assists.at(-1).session) {
        commands.push({ kind: 'assist', session, target, token: 'choice' }); shortcuts['KRect-app-command']();
    }
    function tick(ms = 200) { clock += ms; if (timers[2].running) timers[2].timeout.emit(); }
    return { ws, work, controller, screens, timers, updates, outlines, initial, pointer, begin, move, open, hover, finish, config,
        assists, addWindow, choose, tick, statuses, chooser: () => chooser };
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

test('bare overlay titles work, but other KRect windows cannot become snap targets', () => {
    for (const caption of ['KRect Snap Bar', 'KRect', 'KRect Snap Bar settings']) {
        const h = desktop({ overlayCaption: caption }); h.begin(); h.hover('left');
        const dragged = { ...h.work.frameGeometry }; h.finish();
        assert.deepEqual(h.work.frameGeometry, caption === 'KRect Snap Bar' ?
            api.zone(h.screens[0].area, [0, 0, .5, 1], 8) : dragged);
    }
});

test('the compositor raises the overlay while keeping the dragged window active', () => {
    const h = desktop(), raised = [];
    h.ws.raiseWindow = w => raised.push(w);
    h.work.keepAbove = true;
    h.begin(); h.hover('left');
    assert.ok(raised.length > 0);
    assert.ok(raised.every(w => w.internalId === 'overlay' && w.keepAbove));
    assert.equal(h.ws.activeWindow, h.work);
    h.finish();
    assert.equal(h.ws.activeWindow, h.work);
    assert.equal(h.work.keepAbove, true);
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

for (const plasma5 of [false, true]) {
    test(`Plasma ${plasma5 ? 5 : 6}: half drop suggests a second window, places it once, and restores both originals`, () => {
        for (const [action, complement] of [['left', 'right'], ['right', 'left'], ['top', 'bottom'], ['bottom', 'top']]) {
            const h = desktop({ plasma5 }), other = h.addWindow('browser');
            const original = { ...other.frameGeometry };
            h.begin(); h.hover(action); h.finish();
            const model = h.assists.at(-1);
            assert.equal(model.visible, true); assert.equal(model.action, complement);
            assert.deepEqual(model.candidates.map(w => w.id), ['browser']);
            assert.equal(h.ws.activeWindow === h.chooser() || h.ws.activeClient === h.chooser(), true);
            h.choose('browser');
            assert.deepEqual(other.frameGeometry, api.zone(h.screens[0].area, api.fractions(complement, 0, false), 8));
            assert.equal(h.assists.at(-1).visible, false);
            h.controller.execute('restore', other); assert.deepEqual(other.frameGeometry, original);
            h.choose('browser', model.session); assert.deepEqual(other.frameGeometry, original, 'old choice cannot move it again');
            h.controller.execute('restore', h.work); assert.deepEqual(h.work.frameGeometry, h.initial);
        }
    });
}

test('assist filters excluded, minimized, dialog, other-context and other-monitor windows', () => {
    for (const plasma5 of [false, true]) {
        const h = desktop({ plasma5, config: { IgnoredApplications: 'ignored' } });
        h.ws.currentActivity = 'work';
        const cases = [{ minimized: true }, { resourceClass: 'ignored' }, { resourceClass: 'krect' },
            { dialog: true }, { normalWindow: false }, { fullScreen: true }, { resizeable: false },
            { desktops: [2], desktop: 2 }, { activities: ['away'] }, { output: h.screens[1], screen: 1 },
            { minSize: { width: 1200, height: 200 } }, { maxSize: { width: 800, height: 900 } }];
        cases.forEach((c, i) => h.addWindow(`excluded-${i}`, c));
        h.addWindow('eligible');
        h.begin(); h.hover('left'); h.finish();
        assert.deepEqual(h.assists.at(-1).candidates.map(w => w.id), ['eligible']);
    }
});

test('no assist for shortcuts, thirds, no candidates, an occupied half, small regions or the disabled preference', () => {
    for (const scenario of ['shortcut', 'third', 'empty', 'occupied', 'small', 'disabled']) {
        const h = desktop({ config: { SnapAssist: scenario !== 'disabled' } });
        if (scenario === 'small') h.screens[0].area.height = 300;
        if (scenario !== 'empty') h.addWindow('browser', scenario === 'occupied' ?
            { frameGeometry: api.zone(h.screens[0].area, [.5, 0, .5, 1], 8) } : {});
        if (scenario === 'shortcut') h.controller.execute('left');
        else { h.begin(); h.hover(scenario === 'third' ? 'first-third' : 'left'); h.finish(); }
        assert.equal(h.assists.some(m => m.visible), false, scenario);
    }
});

test('skip leaves both frames alone and returns focus to the first window', () => {
    const h = desktop(), other = h.addWindow('browser');
    h.begin(); h.hover('left'); h.finish();
    const first = { ...h.work.frameGeometry }, second = { ...other.frameGeometry };
    h.choose('');
    assert.deepEqual(h.work.frameGeometry, first); assert.deepEqual(other.frameGeometry, second);
    assert.equal(h.ws.activeWindow, h.work);
    assert.equal(h.assists.at(-1).visible, false);
});

test('closed or changed candidates are revalidated at selection time', () => {
    for (const change of [w => { w.minimized = true; }, w => { w.deleted = true; },
        w => { w.desktops = [2]; }, w => { w.resizeable = false; }, w => { w.minSize = { width: 1200, height: 100 }; }]) {
        const h = desktop(), other = h.addWindow('browser'); h.addWindow('remaining');
        h.begin(); h.hover('left'); h.finish();
        const original = { ...other.frameGeometry }; change(other); h.choose('browser');
        assert.deepEqual(other.frameGeometry, original);
        assert.deepEqual(h.assists.at(-1).candidates.map(w => w.id), ['remaining']);
    }
});

test('context, focus, source geometry and settings changes invalidate the suggestion', () => {
    for (const change of [h => h.ws.currentDesktopChanged.emit(), h => h.ws.screensChanged.emit(),
        h => h.ws.windowRemoved.emit(h.work), h => { h.work.frameGeometry.x += 20; },
        h => { h.config.SnapAssist = false; }, h => { h.screens[0].area.y += 10; },
        h => { const w = h.addWindow('outside'); h.ws.activeWindow = w; h.ws.windowActivated.emit(w); }]) {
        const h = desktop(), other = h.addWindow('browser');
        h.begin(); h.hover('left'); h.finish(); const session = h.assists.at(-1).session;
        const original = { ...other.frameGeometry }; change(h); h.tick(); h.choose('browser', session);
        assert.deepEqual(other.frameGeometry, original); assert.equal(h.assists.at(-1).visible, false);
    }
});

test('hiding the chooser before its asynchronous command does not lose the selection', () => {
    const h = desktop(), other = h.addWindow('browser');
    h.begin(); h.hover('left'); h.finish(); const session = h.assists.at(-1).session;
    h.ws.windowRemoved.emit(h.chooser()); h.ws.activeWindow = h.work;
    h.choose('browser', session);
    assert.deepEqual(other.frameGeometry, api.zone(h.screens[0].area, [.5, 0, .5, 1], 8));
});

test('unacknowledged or constrained first frames cannot offer an overlapping second window', () => {
    for (const acknowledge of [true, false]) {
        const h = desktop(); h.addWindow('browser');
        h.begin(); h.hover('left');
        let actual = { ...h.work.frameGeometry }, requested;
        Object.defineProperty(h.work, 'frameGeometry', { get: () => actual, set: value => { requested = value; } });
        h.finish(); assert.equal(h.assists.some(m => m.visible), false);
        if (acknowledge) actual = requested;
        h.tick(1100);
        assert.equal(h.assists.some(m => m.visible), acknowledge);
    }
});

test('candidate minimum size includes decoration extents', () => {
    const h = desktop();
    h.addWindow('border-too-wide', { minSize: { width: 940, height: 100 },
        clientGeometry: { x: 0, y: 0, width: 620, height: 440 } });
    h.begin(); h.hover('left'); h.finish();
    assert.equal(h.assists.some(m => m.visible), false);
});

test('second-window placement waits for acceptance; refusal rolls back without changing the first window', () => {
    for (const acknowledge of [true, false]) {
        const h = desktop(), other = h.addWindow('browser', { frameGeometry: { ...h.initial, width: 1200 } });
        h.begin(); h.hover('left'); h.finish();
        const first = { ...h.work.frameGeometry }, before = { ...other.frameGeometry };
        let actual = { ...before }, requested;
        Object.defineProperty(other, 'frameGeometry', { get: () => actual, set: value => {
            requested = value;
            if (!acknowledge) actual = { ...value, width: Math.max(1200, value.width) };
        } });
        h.choose('browser');
        assert.equal(h.statuses.some(s => s.result?.token === 'choice'), false, 'do not report success before acceptance');
        if (acknowledge) actual = requested;
        h.tick(1100);
        assert.equal(h.statuses.at(-1).result.success, acknowledge);
        assert.deepEqual(h.work.frameGeometry, first);
        if (!acknowledge) {
            assert.deepEqual(other.frameGeometry, before);
            assert.equal(h.controller.execute('restore', other), false, 'failed placement adds no restore state');
        }
    }
});

test('switching tasks during a delayed second placement never steals focus back', () => {
    const h = desktop(), other = h.addWindow('browser');
    h.begin(); h.hover('left'); h.finish();
    const before = { ...other.frameGeometry };
    Object.defineProperty(other, 'frameGeometry', { get: () => before, set() {} });
    h.choose('browser');
    const outside = h.addWindow('another-task');
    h.ws.activeWindow = outside; h.ws.windowActivated.emit(outside);
    h.tick(1100);
    assert.equal(h.ws.activeWindow, outside);
    assert.equal(h.statuses.filter(s => s.result?.token === 'choice').at(-1).result.success, false);
    assert.deepEqual(other.frameGeometry, before);
});
