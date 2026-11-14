const assert = require('node:assert/strict');
const { test } = require('node:test');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const api = require('../src/main.js');

function signal() {
    const callbacks = [];
    return { connect(f) { callbacks.push(f); }, emit(...args) { callbacks.forEach(f => f(...args)); } };
}

function harness({ config = {}, delayed = false, legacy = false, screens } = {}) {
    screens ||= [
        { name: 'DP-1', geometry: { x: 0, y: 0, width: 1920, height: 1080 }, area: { x: 0, y: 40, width: 1920, height: 1040 } },
        { name: 'DP-2', geometry: { x: 1920, y: -200, width: 2560, height: 1440 }, area: { x: 1920, y: -200, width: 2560, height: 1400 } }
    ];
    let time = 1000;
    const shortcuts = new Map(), logs = [], menus = [];
    const ws = {
        screens, currentDesktop: { id: 'desktop-1' }, activeScreen: screens[0], stackingOrder: [],
        windowAdded: signal(), windowRemoved: signal(),
        clientArea(kind, output) { assert.equal(kind, 2); return { ...(output.area || output.output.area) }; },
        sendClientToScreen(w, output) { w.output = output; }
    };
    function window(overrides = {}) {
        let geometry = { x: 280, y: 180, width: 1000, height: 700 }, pending;
        let mode = 0;
        const w = {
            internalId: `window-${ws.stackingOrder.length + 1}`, output: screens[0],
            managed: true, normalWindow: true, moveable: true, resizeable: true,
            moveableAcrossScreens: true, maximizable: true, resourceClass: 'konsole',
            interactiveMoveResizeFinished: signal(), maximizedAboutToChange: signal(),
            tile: null,
            get frameGeometry() { return { ...geometry }; },
            set frameGeometry(r) {
                assert.ok(Number.isFinite(r.x) && r.width > 0 && r.height > 0);
                if (delayed) pending = { ...r }; else geometry = { ...r };
            },
            commit() { if (pending) { geometry = pending; pending = undefined; } },
            get actualMode() { return mode; },
            setMaximize(v, h) {
                mode = Number(v) + 2 * Number(h);
                w.maximizedAboutToChange.emit(mode);
                if (mode === 3) w.frameGeometry = w.output.area;
            },
            ...overrides
        };
        if (!legacy) Object.defineProperty(w, 'maximizeMode', { get: () => mode });
        ws.stackingOrder.push(w);
        return w;
    }
    const w = window(); ws.activeWindow = w;
    const env = {
        workspace: ws, KWin: { MaximizeArea: 2 }, now: () => time,
        readConfig: (k, fallback) => Object.hasOwn(config, k) ? config[k] : fallback,
        registerShortcut: (id, label, key, callback) => { shortcuts.set(id, { label, key, callback }); return true; },
        registerUserActionsMenu: callback => menus.push(callback), log: text => logs.push(text)
    };
    const controller = api.start(env);
    return { ws, w, window, env, controller, shortcuts, logs, menus, advance: ms => { time += ms; } };
}

test('odd-size halves and thirds share exact boundaries, including negative origins', () => {
    for (let width = 301; width < 380; width++) {
        const a = { x: -3441, y: -127, width, height: 997 };
        for (const count of [2, 3]) {
            const r = Array.from({ length: count }, (_, i) => api.zone(a, [i / count, 0, 1 / count, 1], 0));
            assert.equal(r[0].x, a.x);
            assert.equal(r.at(-1).x + r.at(-1).width, a.x + a.width);
            for (let i = 1; i < r.length; i++) assert.equal(r[i - 1].x + r[i - 1].width, r[i].x);
        }
    }
});

test('outer and internal gaps remain correct for odd and even gap sizes', () => {
    const a = { x: -1920, y: 31, width: 1921, height: 1049 };
    for (let gap = 0; gap < 20; gap++) {
        const left = api.zone(a, [0, 0, 0.5, 1], gap);
        const right = api.zone(a, [0.5, 0, 0.5, 1], gap);
        assert.equal(left.x - a.x, gap);
        assert.equal(right.x - (left.x + left.width), gap);
        assert.equal(a.x + a.width - right.x - right.width, gap);
    }
});

test('all layout targets stay positive and inside small, scaled and negative areas', () => {
    const areas = [{ x: -250, y: -99, width: 11, height: 7 },
        { x: -1536.5, y: 22.5, width: 1536.5, height: 831.5 },
        { x: 0, y: 0, width: 3440, height: 1440 }];
    for (const area of areas) for (const [action] of api.actions) for (let cycle = 0; cycle < 3; cycle++) {
        const f = api.fractions(action, cycle, area.height > area.width);
        if (!f) continue;
        const r = api.zone(area, f, 64);
        assert.ok(r.width > 0 && r.height > 0, action);
        assert.ok(r.x >= area.x && r.y >= area.y, action);
        assert.ok(r.x + r.width <= area.x + area.width && r.y + r.height <= area.y + area.height, action);
    }
});

test('18 unique shortcuts are registered', () => {
    const h = harness();
    assert.equal(h.shortcuts.size, 18);
    assert.equal(new Set([...h.shortcuts.values()].map(s => s.key)).size, 18);
    h.shortcuts.get('KRect-left').callback();
    assert.deepEqual(h.w.frameGeometry, { x: 8, y: 48, width: 948, height: 1024 });
});

test('halves cycle, time out, and restore the first original placement', () => {
    const h = harness({ config: { Gap: 0 } }), initial = h.w.frameGeometry;
    for (const width of [960, 1280, 640, 960]) {
        assert.equal(h.controller.execute('left'), true);
        assert.equal(h.w.frameGeometry.width, width);
        h.advance(100);
    }
    h.advance(1500);
    h.controller.execute('left');
    assert.equal(h.w.frameGeometry.width, 960);
    h.controller.execute('right'); h.controller.execute('maximize'); h.controller.execute('restore');
    assert.deepEqual(h.w.frameGeometry, initial);
    assert.equal(h.w.actualMode, 0);
    assert.equal(h.controller.execute('restore'), false);
});

test('Wayland delayed geometry acknowledgements do not block rapid cycling', () => {
    const h = harness({ config: { Gap: 0 }, delayed: true });
    h.controller.execute('left'); h.advance(30); h.controller.execute('left'); h.w.commit();
    assert.equal(h.w.frameGeometry.width, 1280);
    assert.deepEqual(h.logs, []);
});

test('string false disables cycling and portrait adaptation', () => {
    const h = harness({ config: { Gap: 0, CycleHalves: 'false' } });
    h.controller.execute('left'); h.controller.execute('left');
    assert.equal(h.w.frameGeometry.width, 960);
});

test('external geometry changes restart the cycle', () => {
    const h = harness({ config: { Gap: 0 } });
    h.controller.execute('left'); h.advance(500);
    h.w.frameGeometry = { x: 100, y: 100, width: 500, height: 500 };
    h.controller.execute('left');
    assert.equal(h.w.frameGeometry.width, 960);
});

test('manual move starts a fresh restore baseline', () => {
    const h = harness(); h.controller.execute('left');
    const manual = { x: 80, y: 90, width: 800, height: 550 };
    h.w.frameGeometry = manual; h.w.interactiveMoveResizeFinished.emit();
    h.controller.execute('right'); h.controller.execute('restore');
    assert.deepEqual(h.w.frameGeometry, manual);
});

test('center preserves size and clears native maximization before placement', () => {
    const h = harness({ config: { Gap: 0 } });
    h.controller.execute('center');
    assert.deepEqual(h.w.frameGeometry, { x: 460, y: 210, width: 1000, height: 700 });
    h.controller.execute('maximize'); h.controller.execute('left');
    assert.equal(h.w.actualMode, 0);
    assert.equal(h.w.frameGeometry.width, 960);
});

test('native maximize state is restored when exposed by KWin', () => {
    const h = harness(); h.w.setMaximize(true, true);
    h.controller.execute('left'); h.controller.execute('restore');
    assert.equal(h.w.actualMode, 3);
});

test('current tile API unmanages the selected window without writing a deprecated property', () => {
    const h = harness(); let selected;
    h.w.tile = { unmanage(w) { selected = w; w.tile = null; } };
    h.controller.execute('left');
    assert.equal(selected, h.w); assert.equal(h.w.tile, null);
});

test('early Plasma 6 clears tile association through the compatibility property', () => {
    const h = harness(); h.w.tile = { name: 'legacy-tile' };
    h.controller.execute('left'); assert.equal(h.w.tile, null);
});

test('early Plasma 6 tracks maximize signals without a readable maximizeMode', () => {
    const h = harness({ legacy: true }); h.w.setMaximize(true, false);
    h.controller.execute('right'); h.controller.execute('restore');
    assert.equal(h.w.actualMode, 1);
});

test('separate windows keep separate restore states and cycles', () => {
    const h = harness({ config: { Gap: 0 } }); const other = h.window(); h.ws.windowAdded.emit(other);
    const original = h.w.frameGeometry;
    h.controller.execute('left'); h.ws.activeWindow = other;
    h.controller.execute('left'); assert.equal(other.frameGeometry.width, 960);
    h.ws.activeWindow = h.w; h.controller.execute('restore');
    assert.deepEqual(h.w.frameGeometry, original);
    assert.equal(other.frameGeometry.width, 960);
});

test('closed window IDs do not inherit restore data', () => {
    const h = harness(); h.controller.execute('left'); h.ws.windowRemoved.emit(h.w);
    assert.equal(h.controller.execute('restore'), false);
});

test('screen transfer preserves layout and restore returns to original output', () => {
    const h = harness({ config: { Gap: 0 } }), original = h.w.frameGeometry;
    h.controller.execute('right'); h.controller.execute('next-screen');
    assert.equal(h.w.output.name, 'DP-2');
    assert.deepEqual(h.w.frameGeometry, { x: 3200, y: -200, width: 1280, height: 1400 });
    h.controller.execute('restore');
    assert.equal(h.w.output.name, 'DP-1'); assert.deepEqual(h.w.frameGeometry, original);
});

test('screen transfer uses fresh geometry if app changed size', () => {
    const h = harness({ config: { Gap: 0 } }); h.controller.execute('left'); h.advance(500);
    h.w.frameGeometry = { x: 480, y: 300, width: 480, height: 260 };
    h.controller.execute('next-screen');
    assert.deepEqual(h.w.frameGeometry, { x: 2560, y: 150, width: 640, height: 350 });
});

test('screen order follows physical coordinates and wraps in both directions', () => {
    const h = harness();
    h.ws.screens.reverse();
    h.controller.execute('previous-screen'); assert.equal(h.w.output.name, 'DP-2');
    h.controller.execute('next-screen'); assert.equal(h.w.output.name, 'DP-1');
});

test('portrait thirds use top / center / bottom and adapt on monitor transfer', () => {
    const h = harness({ config: { Gap: 0 } });
    h.ws.screens[1].area = { x: 1920, y: 0, width: 1080, height: 1920 };
    h.controller.execute('center-third'); h.controller.execute('next-screen');
    assert.deepEqual(h.w.frameGeometry, { x: 1920, y: 640, width: 1080, height: 640 });
});

test('unplugged original output restores within the remaining output', () => {
    const h = harness(); h.controller.execute('left'); h.controller.execute('next-screen');
    h.ws.screens = [h.ws.screens[1]];
    assert.equal(h.controller.execute('restore'), true);
    const r = h.w.frameGeometry, a = h.w.output.area;
    assert.ok(r.x >= a.x && r.y >= a.y && r.x + r.width <= a.x + a.width && r.y + r.height <= a.y + a.height);
});

test('single monitor screen movement is a no-op and does not create restore state', () => {
    const h = harness(); h.ws.screens = [h.ws.screens[0]];
    assert.equal(h.controller.execute('next-screen'), false);
    assert.equal(h.controller.execute('restore'), false);
});

test('panel/work-area changes recompute placement and restore on-screen', () => {
    const h = harness({ config: { Gap: 0 } }); h.controller.execute('left');
    h.ws.screens[0].area = { x: 60, y: 0, width: 1860, height: 1080 };
    h.controller.execute('left'); assert.equal(h.w.frameGeometry.x, 60);
    assert.equal(h.w.frameGeometry.width, 930);
    h.controller.execute('restore'); assert.ok(h.w.frameGeometry.x >= 60);
});

for (const override of [{ fullScreen: true }, { dock: true, normalWindow: false, specialWindow: true },
    { resizeable: false }, { moveable: false }, { deleted: true }, { managed: false }, { minimized: true }, { move: true }]) {
    test(`ineligible window is untouched: ${JSON.stringify(override)}`, () => {
        const h = harness(); Object.assign(h.w, override); const original = h.w.frameGeometry;
        assert.equal(h.controller.execute('left'), false); assert.deepEqual(h.w.frameGeometry, original);
    });
}

test('ignored identifiers match exactly and case-insensitively', () => {
    const h = harness({ config: { IgnoredApplications: 'Firefox, KONSOLE' } });
    assert.equal(h.controller.execute('left'), false);
    h.w.resourceClass = 'my-konsole';
    assert.equal(h.controller.execute('left'), true);
});

test('no active window, unknown action and invalid work area are no-ops', () => {
    const h = harness(); h.ws.activeWindow = null;
    assert.equal(h.controller.execute('left'), false); h.ws.activeWindow = h.w;
    assert.equal(h.controller.execute('unknown'), false);
    h.ws.screens[0].area.width = 0;
    assert.equal(h.controller.execute('left'), false);
});

test('menu targets the selected window even if another window becomes active', () => {
    const h = harness(), selected = h.w, other = h.window();
    const menu = h.menus[0](selected); h.ws.activeWindow = other;
    menu.items.find(item => item.text === 'Right half / cycle widths').triggered();
    assert.equal(selected.frameGeometry.x, 964); assert.equal(other.frameGeometry.x, 280);
});

test('KWin entry point registers shortcuts without CommonJS or browser globals', () => {
    const h = harness(); const registrations = [];
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/main.js'), 'utf8'), {
        workspace: h.ws, KWin: h.env.KWin, readConfig: h.env.readConfig,
        registerShortcut: (...args) => { registrations.push(args); return true; },
        registerUserActionsMenu: () => {}, console: { log() {} }
    });
    assert.equal(registrations.length, 18);
});
