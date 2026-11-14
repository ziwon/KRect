const assert = require('node:assert/strict');
const { test } = require('node:test');
const api = require('../src/main.js');

function signal() {
    const listeners = [];
    return { connect(fn) { listeners.push(fn); }, emit(...args) { listeners.forEach(fn => fn(...args)); } };
}

function desktop() {
    const outputs = [
        { geometry: { x: 0, y: 1680, width: 3840, height: 2160 }, area: { x: 0, y: 1720, width: 3840, height: 2120 } },
        { geometry: { x: 3840, y: 0, width: 2160, height: 3840 }, area: { x: 3840, y: 0, width: 2160, height: 3840 } }
    ];
    const clients = [], logs = [];
    const ws = {
        numScreens: 2, currentDesktop: 1, activeClient: null,
        clientAdded: signal(), clientRemoved: signal(),
        clientList() { return clients; },
        clientArea(kind, index, desktop) {
            assert.equal(desktop, 1); assert.equal(typeof index, 'number');
            return { ...outputs[index][kind === 5 ? 'geometry' : 'area'] };
        },
        sendClientToScreen(w, index) { assert.equal(typeof index, 'number'); w.screen = index; }
    };
    function window(id) {
        const w = {
            internalId: id, screen: 0, frameGeometry: { x: 240, y: 1900, width: 900, height: 600 },
            normalWindow: true, managed: true, moveable: true, resizeable: true,
            moveableAcrossScreens: true, maximizable: true,
            clientMaximizedStateAboutToChange: signal(), clientFinishUserMovedResized: signal(),
            mode: 0, setMaximize(v, h) { this.mode = Number(v) + 2 * Number(h); this.clientMaximizedStateAboutToChange.emit(this, this.mode); }
        };
        clients.push(w); return w;
    }
    const w = window('one'); ws.activeClient = w;
    const controller = api.start({ workspace: ws, KWin: { MaximizeArea: 2, ScreenArea: 5 },
        readConfig: (key, fallback) => key === 'Gap' ? 0 : fallback,
        registerShortcut() { return true; }, log: message => logs.push(message) });
    return { outputs, clients, ws, w, window, controller, logs };
}

test('Plasma 5 targets activeClient and handles screen zero, portrait transfer and restore', () => {
    const h = desktop(), original = { ...h.w.frameGeometry };
    assert.equal(h.controller.execute('right'), true);
    assert.deepEqual(h.w.frameGeometry, { x: 1920, y: 1720, width: 1920, height: 2120 });
    h.controller.execute('center-third'); h.controller.execute('next-screen');
    assert.equal(h.w.screen, 1);
    assert.deepEqual(h.w.frameGeometry, { x: 3840, y: 1280, width: 2160, height: 1280 });
    h.controller.execute('restore');
    assert.equal(h.w.screen, 0); assert.deepEqual(h.w.frameGeometry, original); assert.deepEqual(h.logs, []);
});

test('Plasma 5 move and maximize signals update the restore baseline', () => {
    const h = desktop(); h.w.setMaximize(true, false);
    h.controller.execute('left'); h.controller.execute('restore'); assert.equal(h.w.mode, 1);
    h.controller.execute('right');
    const manual = { x: 60, y: 1800, width: 700, height: 500 };
    h.w.frameGeometry = manual; h.w.clientFinishUserMovedResized.emit(h.w);
    h.controller.execute('left'); h.controller.execute('restore'); assert.deepEqual(h.w.frameGeometry, manual);
});

test('Plasma 5 clientAdded and clientRemoved isolate state across window lifetimes', () => {
    const h = desktop(), w = h.window('two'); h.ws.clientAdded.emit(w); h.ws.activeClient = w;
    h.controller.execute('left'); h.ws.clientRemoved.emit(w);
    assert.equal(h.controller.execute('restore'), false);
    assert.equal(h.w.frameGeometry.width, 900);
});

test('Plasma 5 restore survives output index reorder and missing original geometry', () => {
    const h = desktop(), original = { ...h.w.frameGeometry };
    h.controller.execute('left'); h.controller.execute('next-screen');
    h.outputs.reverse(); h.w.screen = 0;
    h.controller.execute('restore'); assert.equal(h.w.screen, 1); assert.deepEqual(h.w.frameGeometry, original);
    h.controller.execute('right'); h.controller.execute('next-screen');
    h.outputs.splice(1, 1); h.ws.numScreens = 1;
    assert.equal(h.controller.execute('restore'), true);
    const r = h.w.frameGeometry, a = h.outputs[0].area;
    assert.ok(r.x >= a.x && r.y >= a.y && r.x + r.width <= a.x + a.width && r.y + r.height <= a.y + a.height);
});
