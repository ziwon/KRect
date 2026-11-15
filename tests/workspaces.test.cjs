const { test } = require('node:test');
const assert = require('node:assert/strict');
const api = require('../src/main.js');
const clone = value => JSON.parse(JSON.stringify(value));

function signal() {
    const handlers = [];
    return { connect(fn) { handlers.push(fn); }, emit(...args) { handlers.forEach(fn => fn(...args)); } };
}

function desktop(plasma5 = false) {
    const desktops = [1, 2, 3, 4].map(n => ({ id: `d${n}`, name: `Mode ${n}` }));
    const output = { name: 'DP-1', geometry: { x: -1600, y: 32, width: 1600, height: 968 } };
    const updates = [], commands = [], shortcuts = {}, timers = [];
    let clock = 1000, sequence = 0;
    const ws = { screens: plasma5 ? undefined : [output], numScreens: 1, desktops: plasma5 ? 4 : desktops,
        desktopName: n => `Mode ${n}`, currentDesktop: plasma5 ? 1 : desktops[0], currentActivity: 'work',
        windowAdded: signal(), windowRemoved: signal(), currentActivityChanged: signal(),
        clientArea: () => ({ ...output.geometry }), stackingOrder: [], clientList: () => ws.stackingOrder,
        sendClientToScreen(w, screen) { w.screen = plasma5 ? screen : 0; w.output = plasma5 ? output : screen; } };
    function add(n, extra = {}) {
        const w = { internalId: `w${n}`, desktopFileName: `app${n}`, resourceClass: `app${n}`, caption: `Window ${n}`,
            managed: true, normalWindow: true, moveable: true, resizeable: true, maximizable: true, minimized: false,
            desktop: n, desktops: [desktops[n - 1]], activities: [], output, screen: 0, maximizeMode: 0,
            frameGeometry: { x: -1500, y: 100, width: 700 + n, height: 500 },
            setMaximize(v, h) { this.maximizeMode = Number(v) + 2 * Number(h); }, ...extra };
        ws.stackingOrder.push(w); ws.windowAdded.emit(w); return w;
    }
    for (let n = 1; n <= 4; n++) add(n);
    ws.activeWindow = ws.activeClient = ws.stackingOrder[0];
    api.start({ workspace: ws, KWin: { MaximizeArea: 0, ScreenArea: 1 }, now: () => clock,
        readConfig: (key, value) => value, registerShortcut: (id, label, key, callback) => { shortcuts[id] = callback; },
        createTimer() { const t = { timeout: signal(), running: false, start() { this.running = true; }, stop() { this.running = false; } }; timers.push(t); return t; },
        callDBus(service, path, iface, method, arg) {
            if (method === 'TakeCommand') arg(JSON.stringify(commands.shift() || {}));
            if (method === 'Update') updates.push(JSON.parse(arg));
        } });
    function command(data) {
        const token = `request-${++sequence}`;
        commands.push({ ...data, token }); shortcuts['KRect-app-command']();
        return updates.findLast(s => s.result?.token === token)?.result;
    }
    function snapshot() { return command({ kind: 'workspace-snapshot' }).snapshot; }
    function apply(saved) {
        const current = snapshot();
        return command({ kind: 'workspace-restore', session: current.session, activity: current.activity,
            placements: saved.windows.map((w, index) => ({ key: `p:${index}`, id: w.id, saved: w,
                expected: current.windows.find(c => c.id === w.id) })) });
    }
    function tick(ms = 2000) { clock += ms; timers.filter(t => t.running).forEach(t => t.timeout.emit()); }
    return { ws, output, desktops, updates, command, snapshot, apply, tick, add };
}

for (const plasma5 of [true, false]) {
    test(`Plasma ${plasma5 ? 5 : 6}: captures four desktops and restores windows without switching desktops or focus`, () => {
        const h = desktop(plasma5), saved = h.snapshot(), active = h.ws.activeWindow, selected = h.ws.currentDesktop;
        assert.equal(saved.desktops.length, 4);
        assert.equal(saved.windows.length, 4);
        h.ws.stackingOrder.forEach(w => {
            w.desktop = 1; w.desktops = [h.desktops[0]];
            w.frameGeometry = { x: -1400, y: 250, width: 600, height: 350 };
        });
        const result = h.apply(saved);
        assert.equal(result.success, true);
        assert.ok(result.rows.every(r => r.status === 'restored'));
        const actual = h.snapshot();
        assert.deepEqual(actual.windows.map(w => [w.desktop, w.geometry]), saved.windows.map(w => [w.desktop, w.geometry]));
        assert.equal(h.ws.currentDesktop, selected);
        assert.equal(h.ws.activeWindow, active);
    });
}

test('snapshots include minimized windows but omit shared, dialog, fullscreen and KRect windows', () => {
    const h = desktop();
    h.ws.stackingOrder[1].minimized = true;
    h.add(1, { internalId: 'all-desktops', desktops: [] });
    h.add(1, { internalId: 'dialog', dialog: true });
    h.add(1, { internalId: 'full', fullScreen: true });
    h.add(1, { internalId: 'krect', desktopFileName: 'org.krect.KRect' });
    h.add(1, { internalId: 'other-activity', activities: ['other'] });
    const saved = h.snapshot();
    assert.equal(saved.windows.length, 4);
    assert.equal(saved.windows[1].minimized, true);
    h.ws.stackingOrder[1].minimized = false;
    assert.equal(h.apply(saved).rows[1].status, 'restored');
    assert.equal(h.ws.stackingOrder[1].minimized, true);
});

test('a stale engine session or malformed batch changes no windows', () => {
    const h = desktop(), saved = h.snapshot(), expected = saved.windows[0];
    const placement = { key: 'p:0', id: expected.id, expected, saved: { ...expected, geometry: { ...expected.geometry, x: -1300 } } };
    assert.equal(h.command({ kind: 'workspace-restore', session: 'stale', activity: saved.activity, placements: [placement] }).success, false);
    const malformed = clone(placement); malformed.id = malformed.expected.id = 'w2'; malformed.saved.geometry.width = '100';
    assert.equal(h.command({ kind: 'workspace-restore', session: saved.session, activity: saved.activity, placements: [placement, malformed] }).success, false);
    assert.deepEqual(h.snapshot().windows, saved.windows);
});

test('windows changed after planning are skipped instead of overriding newer user choices', () => {
    const h = desktop(), saved = h.snapshot(), w = h.ws.stackingOrder[0];
    w.frameGeometry.x += 100;
    const result = h.command({ kind: 'workspace-restore', session: saved.session, activity: saved.activity,
        placements: [{ key: 'p:0', id: w.internalId, expected: saved.windows[0], saved: saved.windows[0] }] });
    assert.equal(result.rows[0].status, 'changed');
    assert.equal(w.frameGeometry.x, saved.windows[0].geometry.x + 100);
});

test('missing monitors map saved geometry into the remaining work area', () => {
    const h = desktop(), saved = h.snapshot();
    saved.windows[0].output = 'removed';
    saved.windows[0].area = { x: 0, y: 0, width: 3200, height: 2000 };
    saved.windows[0].geometry = { x: 1600, y: 100, width: 1500, height: 1600 };
    const result = h.apply(saved);
    assert.equal(result.rows[0].status, 'restored');
    assert.equal(result.rows[0].fallback, true);
    const g = h.ws.stackingOrder[0].frameGeometry;
    assert.ok(g.x >= -1600 && g.x + g.width <= 0 && g.y >= 32 && g.y + g.height <= 1000);
});

test('a delayed refused resize rolls back geometry and desktop and reports failure', () => {
    const h = desktop(), saved = h.snapshot(), w = h.ws.stackingOrder[0], before = clone(w.frameGeometry);
    saved.windows = [saved.windows[0]];
    saved.windows[0].desktop = 'd2'; saved.windows[0].geometry.x += 100;
    Object.defineProperty(w, 'frameGeometry', { get: () => ({ ...before }), set() {} });
    assert.equal(h.apply(saved), undefined, 'no success before the frame is acknowledged');
    h.tick();
    assert.equal(h.updates.at(-1).result.rows[0].status, 'failed');
    assert.deepEqual(w.frameGeometry, before);
    assert.equal(w.desktops[0], h.desktops[0]);
});

test('stopping restoration keeps completed placements and cancels pending ones', () => {
    const h = desktop(), saved = h.snapshot(), before = clone(h.ws.stackingOrder[1].frameGeometry);
    saved.windows.forEach(w => { w.geometry.x += 100; });
    Object.defineProperty(h.ws.stackingOrder[1], 'frameGeometry', { get: () => ({ ...before }), set() {} });
    h.apply(saved);
    h.command({ kind: 'workspace-cancel' });
    assert.equal(h.ws.stackingOrder[0].frameGeometry.x, saved.windows[0].geometry.x);
    assert.deepEqual(h.ws.stackingOrder[1].frameGeometry, before);
    const rows = h.updates.findLast(s => s.result?.rows).result.rows;
    assert.equal(rows.filter(r => r.status === 'restored').length, 3);
    assert.equal(rows.filter(r => r.status === 'cancelled').length, 1);
});
