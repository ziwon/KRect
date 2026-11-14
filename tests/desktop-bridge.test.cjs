const { test } = require('node:test');
const assert = require('node:assert/strict');
const api = require('../src/main.js');

function signal() {
    const handlers = [];
    return { connect(fn) { handlers.push(fn); }, emit(...args) { handlers.forEach(fn => fn(...args)); } };
}

function desktop(plasma5 = false) {
    const output = { name: 'HDMI-1', geometry: { x: 0, y: 0, width: 1600, height: 1000 } };
    const shortcuts = {}, updates = [], commands = [];
    const desktopId = plasma5 ? 1 : {};
    function window(id, extra = {}) {
        return { internalId: id, caption: id, managed: true, normalWindow: true, output, screen: 0,
            frameGeometry: { x: 100, y: 100, width: 600, height: 400 },
            moveable: true, resizeable: true, maximizable: true, moveableAcrossScreens: true,
            desktop: 1, desktops: plasma5 ? undefined : [desktopId], activities: [],
            setMaximize(v, h) { this.maximizeMode = Number(v)+2*Number(h); }, ...extra };
    }
    const work = window('work');
    const app = window('app', { desktopFileName: 'org.krect.KRect', resourceClass: 'krect' });
    const ws = { screens: plasma5 ? undefined : [output], numScreens: 1, currentDesktop: desktopId,
        currentActivity: 'writing', stackingOrder: [work, app], clientList: () => [work, app],
        activeWindow: work, activeClient: work, windowActivated: signal(), windowRemoved: signal(),
        currentDesktopChanged: signal(), clientMaximizeSet: plasma5 ? signal() : undefined,
        clientArea: () => ({ ...output.geometry }) };
    const controller = api.start({ workspace: ws, KWin: { MaximizeArea: 0, ScreenArea: 1 },
        readConfig: (k, fallback) => k === 'IgnoredApplications' ? 'ignored' : fallback,
        registerShortcut: (id, label, key, callback) => { shortcuts[id] = callback; },
        callDBus: (service, path, iface, method, arg) => {
            assert.equal(service, 'org.krect.KRect');
            if (method === 'Update') updates.push(JSON.parse(arg));
            else if (method === 'TakeCommand') arg(JSON.stringify(commands.shift() || {}));
        } });
    function activate(w) { ws.activeWindow = ws.activeClient = w; ws.windowActivated.emit(w); }
    function apply(action, target = 'work') {
        commands.push({ token: 'request', action, target }); shortcuts['KRect-app-command']();
        return updates.at(-1);
    }
    return { ws, work, app, window, activate, apply, updates, shortcuts, controller };
}

test('desktop buttons arrange the remembered work window, never the KRect window', () => {
    const h = desktop(), appFrame = { ...h.app.frameGeometry };
    h.activate(h.app);
    assert.equal(h.apply('left').result.success, true);
    assert.equal(h.work.frameGeometry.width, 788);
    assert.deepEqual(h.app.frameGeometry, appFrame);
    assert.equal(h.controller.execute('right'), false, 'regular keyboard commands do not fall back to an unrelated window');
    assert.equal(h.apply('restore').result.success, true);
    assert.deepEqual(h.work.frameGeometry, { x: 100, y: 100, width: 600, height: 400 });
});

test('a focus change rejects a command aimed at the previously reported window', () => {
    const h = desktop(), other = h.window('other');
    h.activate(other); h.activate(h.app);
    assert.equal(h.apply('left', 'work').result.success, false);
    assert.equal(h.work.frameGeometry.width, 600);
    assert.equal(other.frameGeometry.width, 600);
});

test('excluded, fullscreen and minimized targets do not reuse an earlier work window', () => {
    for (const extra of [{ resourceClass: 'ignored' }, { fullScreen: true }, { minimized: true }]) {
        const h = desktop(); h.activate(h.window('blocked', extra)); h.activate(h.app);
        assert.equal(h.apply('left').result.success, false);
        assert.equal(h.updates.at(-1).target, null);
    }
});

test('desktop app does not arrange a window on another desktop or activity', () => {
    for (const plasma5 of [false, true]) {
        const h = desktop(plasma5); h.activate(h.app);
        h.ws.currentDesktop = plasma5 ? 2 : {};
        h.ws.currentDesktopChanged.emit();
        assert.equal(h.apply('left').result.success, false);
    }
    const h = desktop(); h.work.activities = ['other-activity'];
    assert.equal(h.apply('left').result.success, false);
});

test('closed targets and unknown commands are rejected without moving a window', () => {
    const h = desktop();
    assert.equal(h.apply('arbitrary-command').result.success, false);
    h.ws.windowRemoved.emit(h.work);
    assert.equal(h.apply('left').result.success, false);
});

test('Plasma 5 boolean maximize signal preserves the native maximize flag on restore', () => {
    const h = desktop(true);
    delete h.work.maximizeMode;
    h.ws.clientMaximizeSet.emit(h.work, true, true);
    h.controller.execute('left'); h.controller.execute('restore');
    assert.equal(h.work.maximizeMode, 3);
});
