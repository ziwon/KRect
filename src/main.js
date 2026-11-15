/* SPDX-License-Identifier: MIT
 * KRect 0.3.1 — window placement for KWin / Plasma 5.27 and 6.
 * This file is both the KWin entry point and a dependency-free Node test module.
 */
(function (root, factory) {
    "use strict";
    var api = factory();
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    } else {
        api.start({
            workspace: workspace,
            KWin: KWin,
            readConfig: readConfig,
            registerShortcut: registerShortcut,
            registerUserActionsMenu: registerUserActionsMenu,
            callDBus: typeof callDBus === "function" ? callDBus : null,
            createTimer: typeof QTimer === "function" ? function () { return new QTimer(); } : null,
            log: function (message) { console.log("KRect: " + message); }
        });
    }
}(this, function () {
    "use strict";

    var ACTIONS = [
        ["left", "Left half / cycle widths", "Ctrl+Alt+Left"],
        ["right", "Right half / cycle widths", "Ctrl+Alt+Right"],
        ["top", "Top half / cycle heights", "Ctrl+Alt+Up"],
        ["bottom", "Bottom half / cycle heights", "Ctrl+Alt+Down"],
        ["top-left", "Top left quarter", "Ctrl+Alt+U"],
        ["top-right", "Top right quarter", "Ctrl+Alt+I"],
        ["bottom-left", "Bottom left quarter", "Ctrl+Alt+J"],
        ["bottom-right", "Bottom right quarter", "Ctrl+Alt+K"],
        ["first-third", "First third", "Ctrl+Alt+D"],
        ["center-third", "Center third", "Ctrl+Alt+F"],
        ["last-third", "Last third", "Ctrl+Alt+G"],
        ["first-two-thirds", "First two thirds", "Ctrl+Alt+E"],
        ["last-two-thirds", "Last two thirds", "Ctrl+Alt+T"],
        ["center", "Center window", "Ctrl+Alt+C"],
        ["maximize", "Maximize window", "Ctrl+Alt+Return"],
        ["restore", "Restore original placement", "Ctrl+Alt+Backspace"],
        ["swap", "Swap with another window", ""],
        ["undo-swap", "Undo window swap", ""],
        ["previous-screen", "Previous screen", "Ctrl+Alt+Shift+Left"],
        ["next-screen", "Next screen", "Ctrl+Alt+Shift+Right"]
    ];

    function rect(r) {
        return { x: Number(r.x), y: Number(r.y), width: Number(r.width), height: Number(r.height) };
    }

    function valid(r) {
        return r && isFinite(r.x) && isFinite(r.y) && isFinite(r.width) &&
            isFinite(r.height) && r.width > 0 && r.height > 0;
    }

    function near(a, b, tolerance) {
        return valid(a) && valid(b) && ["x", "y", "width", "height"].every(function (k) {
            return Math.abs(a[k] - b[k]) <= tolerance;
        });
    }

    function bounded(value, fallback, low, high) {
        var n = Number(value);
        return isFinite(n) ? Math.max(low, Math.min(high, n)) : fallback;
    }

    function boolean(value) {
        return value === true || value === 1 || value === "true" || value === "1";
    }

    function fit(r, area) {
        var w = Math.min(r.width, area.width);
        var h = Math.min(r.height, area.height);
        return {
            x: Math.max(area.x, Math.min(area.x + area.width - w, r.x)),
            y: Math.max(area.y, Math.min(area.y + area.height - h, r.y)),
            width: w, height: h
        };
    }

    // Round shared boundaries, not widths: adjacent tiles cover odd-sized areas.
    // Outer margins are one gap; each internal edge contributes half a gap.
    function zone(area, fractions, requestedGap) {
        var gap = Math.floor(bounded(requestedGap, 0, 0, Math.min(64, area.width / 12, area.height / 12)));
        var x0 = fractions[0], y0 = fractions[1];
        var x1 = x0 + fractions[2], y1 = y0 + fractions[3];
        var left = Math.round(area.x + area.width * x0 + (x0 === 0 ? gap : gap / 2));
        var top = Math.round(area.y + area.height * y0 + (y0 === 0 ? gap : gap / 2));
        var right = Math.round(area.x + area.width * x1 - (x1 === 1 ? gap : gap / 2));
        var bottom = Math.round(area.y + area.height * y1 - (y1 === 1 ? gap : gap / 2));
        return fit({ x: left, y: top, width: Math.max(1, right - left), height: Math.max(1, bottom - top) }, area);
    }

    function fractions(action, index, portrait) {
        var size = [1 / 2, 2 / 3, 1 / 3][index || 0];
        var layouts = {
            "left": [0, 0, size, 1], "right": [1 - size, 0, size, 1],
            "top": [0, 0, 1, size], "bottom": [0, 1 - size, 1, size],
            "top-left": [0, 0, 1 / 2, 1 / 2], "top-right": [1 / 2, 0, 1 / 2, 1 / 2],
            "bottom-left": [0, 1 / 2, 1 / 2, 1 / 2], "bottom-right": [1 / 2, 1 / 2, 1 / 2, 1 / 2],
            "first-third": [0, 0, 1 / 3, 1], "center-third": [1 / 3, 0, 1 / 3, 1],
            "last-third": [2 / 3, 0, 1 / 3, 1], "first-two-thirds": [0, 0, 2 / 3, 1],
            "last-two-thirds": [1 / 3, 0, 2 / 3, 1]
        };
        var f = layouts[action];
        if (f && portrait && action.indexOf("third") !== -1) {
            return [f[1], f[0], f[3], f[2]];
        }
        return f;
    }

    function mapRect(r, from, to) {
        return fit({
            x: to.x + (r.x - from.x) / from.width * to.width,
            y: to.y + (r.y - from.y) / from.height * to.height,
            width: r.width / from.width * to.width,
            height: r.height / from.height * to.height
        }, to);
    }

    function contains(r, p) {
        return r && p && p.x >= r.x && p.y >= r.y && p.x < r.x + r.width && p.y < r.y + r.height;
    }

    // The compositor owns these coordinates, including on scaled X11 desktops.
    // The app paints this same model instead of maintaining a second hit map.
    function snapLayout(area, portrait) {
        var groups = [["left", "right"], ["top", "bottom"],
            ["first-third", "center-third", "last-third"],
            ["first-two-thirds", "last-third"], ["first-third", "last-two-thirds"],
            ["top-left", "top-right", "bottom-left", "bottom-right"]];
        var width = Math.min(648, area.width - 24), height = 120;
        if (width < 360 || area.height < height + 80) { return null; }
        var bar = { x: Math.round(area.x + (area.width - width) / 2), y: area.y + 12, width: width, height: height };
        var cardWidth = (width - 24 - 5 * 12) / 6;
        var cells = [];
        groups.forEach(function (actions, group) {
            var card = { x: 12 + group * (cardWidth + 12), y: 38, width: cardWidth, height: 62 };
            actions.forEach(function (action) {
                var f = fractions(action, 0, portrait);
                cells.push({ action: action, group: group, rect: zone(card, f, 3) });
            });
        });
        return { geometry: bar, cells: cells };
    }

    function start(env) {
        var ws = env.workspace;
        var plasma5 = typeof ws.screens === "undefined";
        var states = Object.create(null);
        var tracked = Object.create(null);
        var now = env.now || function () { return Date.now(); };
        var cfg = env.readConfig;
        var lastWindow = null;
        var drag = null, overlay = null, dragSerial = 0, updatingDrag = false;
        var snapTimer = env.createTimer && env.callDBus ? env.createTimer() : null;
        var dropTimer = snapTimer ? env.createTimer() : null;
        var pendingDrop = null;
        var assist = null, assistWindow = null, assistSerial = 0;
        var pairPlacement = null;
        var assistTimer = snapTimer ? env.createTimer() : null;
        var swapPlacement = null, swapUndo = null;
        var workspaceTimer = snapTimer ? env.createTimer() : null, workspaceRestore = null;
        var workspaceSession = String(now()) + "-" + Math.random().toString(36).slice(2);

        function ownWindow(w) {
            return w && [w.resourceClass, w.resourceName, w.desktopFileName].some(function (value) {
                return /^(org\.krect\.krect|krect)$/.test(String(value || "").toLowerCase());
            });
        }

        function currentContext(w) {
            if (!w) { return false; }
            if (plasma5 && typeof w.desktop === "number" && w.desktop !== -1 && w.desktop !== ws.currentDesktop) { return false; }
            if (!plasma5 && w.desktops && w.desktops.length &&
                    Array.prototype.indexOf.call(w.desktops, ws.currentDesktop) === -1) { return false; }
            return !w.activities || !w.activities.length || !ws.currentActivity ||
                Array.prototype.indexOf.call(w.activities, ws.currentActivity) !== -1;
        }

        function appTarget() {
            return currentContext(lastWindow) && eligible(lastWindow, settings()) ? lastWindow : null;
        }

        function publish(result) {
            if (!env.callDBus) { return; }
            var w = appTarget();
            var output = w ? screenFor(w) : null;
            var status = { protocol: 1, version: "0.4.0-rc.2", snapBar: 1, snapAssist: 1, windowSwap: 1, workspacePresets: 1,
                desktops: desktopList().map(desktopInfo), currentDesktop: desktopKey(ws.currentDesktop), activity: String(ws.currentActivity || ""), target: w ? {
                id: id(w), caption: String(w.caption || w.resourceClass || "Window"),
                application: String(w.desktopFileName || w.resourceClass || ""),
                geometry: rect(w.frameGeometry), area: areaFor(output, w), screen: name(output),
                canRestore: Boolean(states[id(w)]), maximizable: Boolean(w.maximizable),
                canSwap: Boolean(assistTimer && swapEligible(w, settings())), canUndoSwap: canUndoSwap(w),
                movableAcrossScreens: Boolean(w.moveableAcrossScreens)
            } : null, screens: screenList().map(function (screen) {
                return { name: name(screen), geometry: rect(screen.geometry), area: areaFor(screen, w) };
            }), result: result || null };
            env.callDBus("org.krect.KRect", "/KRect", "org.krect.KRect", "Update", JSON.stringify(status));
        }

        function activated(w) {
            if (swapPlacement && w && !ownWindow(w) && !swapPlacement.entries.some(function (e) { return e.window === w; })) {
                cancelSwap(true);
            }
            if (pairPlacement && w && w !== pairPlacement.window && w !== pairPlacement.source && w !== assistWindow) {
                cancelPair(true);
            }
            if (assist && w && w !== assist.source && w !== assistWindow && !(assist.action === "swap" && ownWindow(w))) { cancelAssist(false); }
            if (ownWindow(w)) { publish(); return; }
            if (w && (w.normalWindow || w.dialog)) { lastWindow = eligible(w, settings()) ? w : null; }
            publish();
        }

        function appCommand() {
            if (!env.callDBus) { return; }
            env.callDBus("org.krect.KRect", "/KRect", "org.krect.KRect", "TakeCommand", function (raw) {
                try {
                    var command = JSON.parse(String(raw || "{}"));
                    if (!command.token) { publish(); return; }
                    if (command.kind === "workspace-snapshot") {
                        publish({ token: command.token, success: true, snapshot: workspaceSnapshot() }); return;
                    }
                    if (command.kind === "workspace-restore") { restoreWorkspace(command); return; }
                    if (command.kind === "workspace-cancel") {
                        cancelWorkspace(); publish({ token: command.token, success: true }); return;
                    }
                    if (command.kind === "assist") {
                        var accepted = assistCommand(command);
                        if (accepted !== null) { publish({ token: command.token, success: accepted, quiet: !command.target }); }
                        return;
                    }
                    var w = appTarget();
                    var known = ACTIONS.some(function (a) { return a[0] === command.action; });
                    var success = known && w && id(w) === command.target ? safeExecute(command.action, w, command.token) : false;
                    if (success !== null) { publish({ token: command.token, success: success, operation: command.action === "swap" ? "choose-swap" : command.action,
                        quiet: success && command.action === "swap" }); }
                } catch (error) { log("Desktop app command failed: " + String(error)); publish(); }
            });
        }

        function settings() {
            return {
                gap: bounded(cfg("Gap", 8), 8, 0, 64),
                cycle: boolean(cfg("CycleHalves", true)),
                timeout: bounded(cfg("CycleTimeout", 1200), 1200, 200, 5000),
                portrait: boolean(cfg("PortraitThirds", true)),
                snapBar: boolean(cfg("SnapBar", true)),
                snapAssist: boolean(cfg("SnapAssist", true)),
                ignored: String(cfg("IgnoredApplications", "")).toLowerCase().split(/[,;\n]/).map(function (s) { return s.trim(); }).filter(Boolean)
            };
        }

        function id(w) { return String(w.internalId); }
        function name(output) { return output ? String(output.name) : ""; }
        function log(message) { if (env.log) { env.log(message); } }

        function eligible(w, opts, allowMove, allowMinimized) {
            if (!w || ownWindow(w) || w.deleted || !w.managed || !(w.normalWindow || w.dialog) ||
                    w.fullScreen || w.specialWindow || (w.minimized && !allowMinimized) || w.shade || (w.move && !allowMove) || w.resize ||
                    !w.moveable || !w.resizeable || !valid(w.frameGeometry)) {
                return false;
            }
            var identifiers = [w.resourceClass, w.resourceName, w.desktopFileName].map(function (s) {
                return String(s || "").toLowerCase();
            });
            return !opts.ignored.some(function (s) { return identifiers.indexOf(s) !== -1; });
        }

        function areaFor(output, w, desktop) {
            var area = output ? ws.clientArea(env.KWin.MaximizeArea, plasma5 ? output.index : output, desktop === undefined ? ws.currentDesktop : desktop) :
                ws.clientArea(env.KWin.MaximizeArea, w);
            return valid(area) ? rect(area) : null;
        }

        function screenList() {
            var screens = [];
            if (plasma5) {
                for (var i = 0; i < ws.numScreens; i++) {
                    var geometry = rect(ws.clientArea(env.KWin.ScreenArea, i, ws.currentDesktop));
                    screens.push({ index: i, geometry: geometry,
                        name: "geometry:" + [geometry.x, geometry.y, geometry.width, geometry.height].join(",") });
                }
            } else {
                screens = Array.prototype.slice.call(ws.screens);
            }
            return screens.sort(function (a, b) {
                return a.geometry.x - b.geometry.x || a.geometry.y - b.geometry.y || name(a).localeCompare(name(b));
            });
        }

        function screenFor(w) {
            if (!plasma5) { return w.output || ws.activeScreen; }
            var screens = screenList();
            for (var i = 0; i < screens.length; i++) {
                if (screens[i].index === w.screen) { return screens[i]; }
            }
            return null;
        }

        function findScreen(outputName) {
            var screens = screenList();
            for (var i = 0; i < screens.length; i++) {
                if (name(screens[i]) === outputName) { return screens[i]; }
            }
            return null;
        }

        function desktopKey(value) { return plasma5 ? String(value) : String(value && value.id || ""); }

        function desktopList() {
            var list = [];
            if (plasma5) {
                var count = typeof ws.desktops === "number" ? ws.desktops : 1;
                for (var n = 1; n <= Math.min(count, 64); n++) {
                    list.push({ value: n, id: String(n), number: n,
                        name: typeof ws.desktopName === "function" ? String(ws.desktopName(n)) : "Desktop " + n });
                }
            } else {
                Array.prototype.forEach.call(ws.desktops || [], function (d, index) {
                    list.push({ value: d, id: String(d.id), number: index + 1, name: String(d.name || "Desktop " + (index + 1)) });
                });
            }
            return list;
        }

        function desktopInfo(d) { return { id: d.id, number: d.number, name: d.name }; }
        function findDesktop(key) { return desktopList().filter(function (d) { return d.id === key; })[0]; }
        function windowDesktop(w) {
            if (plasma5) { return w.desktop > 0 ? String(w.desktop) : ""; }
            return w.desktops && w.desktops.length === 1 ? desktopKey(w.desktops[0]) : "";
        }
        function setDesktop(w, d) { if (plasma5) { w.desktop = d.value; } else { w.desktops = [d.value]; } }
        function allWindows() { return Array.prototype.slice.call(plasma5 ? ws.clientList() : ws.stackingOrder || []); }
        function sameActivity(w) {
            return !w.activities || !w.activities.length || !ws.currentActivity ||
                Array.prototype.indexOf.call(w.activities, ws.currentActivity) !== -1;
        }
        function workspaceEligible(w) {
            return eligible(w, settings(), false, true) && tracked[id(w)] && w.normalWindow && !w.dialog &&
                !w.tile && sameActivity(w) && Boolean(windowDesktop(w)) && Boolean(w.desktopFileName || w.resourceClass);
        }
        function workspaceWindow(w) {
            var d = findDesktop(windowDesktop(w)), output = screenFor(w), area = d && areaFor(output, w, d.value);
            if (!area) { return null; }
            var mode = maxMode(w);
            if (mode === null || mode === undefined) {
                mode = Number(Boolean(w.maximizedVertically)) + 2 * Number(Boolean(w.maximizedHorizontally));
            }
            return { id: id(w), application: String(w.desktopFileName || "").slice(0, 512),
                resourceClass: String(w.resourceClass || "").slice(0, 512), role: String(w.windowRole || "").slice(0, 512),
                caption: String(w.caption || "").slice(0, 512), desktop: d.id, output: name(output),
                geometry: rect(w.frameGeometry), area: area, mode: mode, minimized: Boolean(w.minimized) };
        }
        function workspaceSnapshot() {
            var windows = allWindows(), saved = windows.filter(workspaceEligible).map(workspaceWindow).filter(Boolean);
            var running = [];
            windows.filter(function (w) { return !ownWindow(w) && sameActivity(w); }).forEach(function (w) {
                running.push(String(w.desktopFileName || ""), String(w.resourceClass || ""));
            });
            return { schema: 1, session: workspaceSession, activity: String(ws.currentActivity || ""),
                currentDesktop: desktopKey(ws.currentDesktop), desktops: desktopList().map(desktopInfo),
                windows: saved.slice(0, 256), truncated: saved.length > 256,
                runningApplications: running.filter(Boolean) };
        }
        function strictGeometry(g) {
            return valid(g) && ["x", "y", "width", "height"].every(function (k) {
                return typeof g[k] === "number" && Math.abs(g[k]) <= 1000000;
            });
        }
        function rollbackWorkspace(entry) {
            var w = entry.window, before = entry.before, d = findDesktop(before.desktop), output = findScreen(before.output);
            if (!workspaceEligible(w) || !d || !output || !near(areaFor(output, w, d.value), before.area, 0)) { return; }
            try {
                w.minimized = false; setDesktop(w, d); place(w, before.geometry, output);
                w.setMaximize(Boolean(before.mode & 1), Boolean(before.mode & 2)); w.minimized = before.minimized;
            } catch (error) { log("Workspace rollback failed: " + String(error)); }
        }
        function finishWorkspace(p) {
            workspaceRestore = null; workspaceTimer.stop();
            publish({ token: p.token, success: true, rows: p.rows });
        }
        function cancelWorkspace() {
            var p = workspaceRestore;
            if (!p) { return; }
            p.entries.forEach(function (entry) {
                rollbackWorkspace(entry); p.rows.push({ key: entry.key, id: id(entry.window), status: "cancelled" });
            });
            finishWorkspace(p);
        }
        function checkWorkspace() {
            var p = workspaceRestore;
            if (!p) { return; }
            p.entries = p.entries.filter(function (entry) {
                var w = entry.window, output = findScreen(entry.output), d = findDesktop(entry.desktop);
                var validContext = p.activity === String(ws.currentActivity || "") && workspaceEligible(w) && d && output &&
                    near(areaFor(output, w, d.value), entry.area, 0);
                if (validContext && windowDesktop(w) === entry.desktop && name(screenFor(w)) === entry.output &&
                        near(w.frameGeometry, entry.target, 2) && (maxMode(w) === null || maxMode(w) === undefined || maxMode(w) === entry.mode)) {
                    var state = states[id(w)] || { original: { geometry: entry.before.geometry, area: entry.before.area,
                        output: entry.before.output, desktop: entry.before.desktop, mode: entry.before.mode }, last: null };
                    states[id(w)] = state;
                    remember(state, "workspace", 0, entry.target, entry.before.geometry, output, entry.area);
                    w.minimized = entry.minimized;
                    p.rows.push({ key: entry.key, id: id(w), status: "restored", fallback: entry.fallback });
                    return false;
                }
                if (!validContext || now() - p.created >= 1800) {
                    rollbackWorkspace(entry); p.rows.push({ key: entry.key, id: id(w), status: "failed" }); return false;
                }
                return true;
            });
            if (!p.entries.length) { finishWorkspace(p); }
        }
        function restoreWorkspace(command) {
            var seen = Object.create(null), placements = command.placements;
            if (!workspaceTimer || workspaceRestore || command.session !== workspaceSession ||
                    command.activity !== String(ws.currentActivity || "") || !Array.isArray(placements) || placements.length > 256 ||
                    !placements.every(function (e) {
                        if (!e || typeof e.key !== "string" || typeof e.id !== "string" || seen[e.id] || !e.saved || !e.expected) { return false; }
                        seen[e.id] = true;
                        return e.expected.id === e.id && strictGeometry(e.expected.geometry) && strictGeometry(e.saved.geometry) &&
                            strictGeometry(e.saved.area) && typeof e.saved.desktop === "string" && typeof e.saved.output === "string" &&
                            typeof e.saved.mode === "number" && [0, 1, 2, 3].indexOf(e.saved.mode) !== -1 && typeof e.saved.minimized === "boolean";
                    })) { publish({ token: command.token, success: false, error: "invalid-or-busy" }); return; }
            cancelPair(true); cancelSwap(true); cancelAssist(false); cancelDrag(); swapUndo = null;
            var p = { token: command.token, activity: command.activity, created: now(), rows: [], entries: [] };
            var windows = allWindows();
            placements.forEach(function (e) {
                var w = windows.filter(function (candidate) { return id(candidate) === e.id; })[0];
                var current = w && workspaceEligible(w) && workspaceWindow(w), d = findDesktop(e.saved.desktop);
                if (!current || !d || current.application !== e.expected.application || current.resourceClass !== e.expected.resourceClass ||
                        current.desktop !== e.expected.desktop || current.caption !== e.expected.caption ||
                        current.mode !== e.expected.mode || current.minimized !== e.expected.minimized ||
                        !near(current.geometry, e.expected.geometry, 2)) {
                    p.rows.push({ key: e.key, id: e.id, status: "changed" }); return;
                }
                var output = findScreen(e.saved.output) || screenFor(w), area = areaFor(output, w, d.value);
                if (!area) { p.rows.push({ key: e.key, id: e.id, status: "output-missing" }); return; }
                var target = near(area, e.saved.area, 0) ? fit(e.saved.geometry, area) : mapRect(e.saved.geometry, e.saved.area, area);
                if (e.saved.mode & 1) { target.y = area.y; target.height = area.height; }
                if (e.saved.mode & 2) { target.x = area.x; target.width = area.width; }
                if (!fitsAssist(w, target) || (e.saved.mode && !w.maximizable)) {
                    p.rows.push({ key: e.key, id: e.id, status: "size-limit" }); return;
                }
                var entry = { key: e.key, window: w, before: current, desktop: d.id, output: name(output),
                    area: area, target: target, mode: e.saved.mode, minimized: e.saved.minimized, fallback: name(output) !== e.saved.output };
                try {
                    w.minimized = false; setDesktop(w, d); place(w, target, output);
                    w.setMaximize(Boolean(e.saved.mode & 1), Boolean(e.saved.mode & 2));
                    p.entries.push(entry);
                } catch (error) { rollbackWorkspace(entry); p.rows.push({ key: e.key, id: e.id, status: "failed" }); }
            });
            workspaceRestore = p; workspaceTimer.start(); checkWorkspace();
        }

        function sendAssist(payload) {
            if (env.callDBus) {
                env.callDBus("org.krect.KRect", "/KRect", "org.krect.KRect", "AssistUpdate", JSON.stringify(payload));
            }
        }

        function cancelAssist(restoreFocus) {
            if (!assist) { return; }
            var source = assist.source;
            assist = null;
            assistTimer.stop();
            if (restoreFocus && (plasma5 ? ws.activeClient : ws.activeWindow) === assistWindow &&
                    tracked[id(source)] && currentContext(source) && eligible(source, settings())) {
                if (plasma5) { ws.activeClient = source; } else { ws.activeWindow = source; }
            }
            sendAssist({ visible: false });
        }

        function positionAssist() {
            if (!assist || !assist.ready || !assistWindow || assistWindow.deleted) { return; }
            assistWindow.keepAbove = true; assistWindow.skipTaskbar = true; assistWindow.skipPager = true;
            assistWindow.noBorder = true;
            if (!near(assistWindow.frameGeometry, assist.popup, 1)) { assistWindow.frameGeometry = rect(assist.popup); }
            if (!assist.focused) {
                assist.focused = true;
                if (plasma5) { ws.activeClient = assistWindow; } else { ws.activeWindow = assistWindow; }
            }
        }

        function assistCandidates(s, opts) {
            return Array.prototype.slice.call(plasma5 ? ws.clientList() : (ws.stackingOrder || [])).reverse().filter(function (w) {
                return w !== s.source && w.normalWindow && !w.dialog && tracked[id(w)] &&
                    currentContext(w) && eligible(w, opts) && name(screenFor(w)) === s.output && fitsAssist(w, s.target) &&
                    (s.action !== "swap" || (swapEligible(w, opts) && fitsAssist(s.source, w.frameGeometry) &&
                        near(fit(w.frameGeometry, s.area), w.frameGeometry, 1) && !near(w.frameGeometry, s.placed, 2)));
            });
        }

        function fitsAssist(w, target) {
            var client = valid(w.clientGeometry) ? w.clientGeometry : w.frameGeometry;
            return ["width", "height"].every(function (dimension) {
                var border = Math.max(0, w.frameGeometry[dimension] - client[dimension]);
                var size = target[dimension] - border;
                var min = w.minSize && w.minSize[dimension], max = w.maxSize && w.maxSize[dimension];
                return !(typeof min === "number" && isFinite(min) && min > size) &&
                    !(typeof max === "number" && isFinite(max) && max > 0 && max < size);
            });
        }

        function cancelPair(rollback) {
            if (!pairPlacement) { return; }
            var p = pairPlacement; pairPlacement = null;
            assistTimer.stop();
            var output = findScreen(p.output), area = output && areaFor(output, p.window);
            if (rollback && tracked[id(p.window)] && currentContext(p.window) && eligible(p.window, settings()) &&
                    area && near(area, p.area, 0)) {
                place(p.window, p.before, output);
                if (p.mode) { p.window.setMaximize(Boolean(p.mode & 1), Boolean(p.mode & 2)); }
            }
            publish({ token: p.token, success: false });
        }

        function checkPair() {
            if (!pairPlacement) { return; }
            var p = pairPlacement, w = p.window, output = findScreen(p.output);
            var area = output && areaFor(output, w), opts = settings();
            var active = plasma5 ? ws.activeClient : ws.activeWindow;
            if (!tracked[id(w)] || !tracked[id(p.source)] || !currentContext(w) || !currentContext(p.source) ||
                    !eligible(w, opts) || !eligible(p.source, opts) || !area || !near(area, p.area, 0) ||
                    !near(p.source.frameGeometry, p.placed, 2) || !fitsAssist(w, p.target) ||
                    (active && active !== w && active !== p.source && active !== assistWindow)) {
                cancelPair(true); return;
            }
            if (!near(w.frameGeometry, p.target, 2)) {
                if (now() - p.created >= 1000) { cancelPair(true); }
                return;
            }
            pairPlacement = null; assistTimer.stop();
            states[id(w)] = p.state;
            remember(p.state, p.action, 0, p.target, p.before, output, area);
            if (plasma5) { ws.activeClient = w; } else { ws.activeWindow = w; }
            lastWindow = w;
            publish({ token: p.token, success: true });
        }

        function updateAssist() {
            if (!assist) { return; }
            var s = assist, opts = settings(), output = findScreen(s.output);
            var area = output && areaFor(output, s.source);
            var active = plasma5 ? ws.activeClient : ws.activeWindow;
            var swapping = s.action === "swap";
            if ((!swapping && (!opts.snapBar || !opts.snapAssist)) || (swapping && !swapEligible(s.source, opts)) ||
                    !tracked[id(s.source)] || !currentContext(s.source) ||
                    !eligible(s.source, opts) || !area || !near(area, s.area, 0) ||
                    (active && active !== s.source && active !== assistWindow && !(swapping && ownWindow(active)))) {
                cancelAssist(false); return;
            }
            if (s.closedAt !== undefined && now() - s.closedAt > 1000) { cancelAssist(true); return; }
            if (swapping && !s.focused && now() - s.created > 2500) { cancelAssist(true); return; }
            // Wait for the real frame (Wayland configure/ack and client size hints).
            if (name(screenFor(s.source)) !== s.output || !near(s.source.frameGeometry, s.placed, 2)) {
                if (s.ready || now() - s.created >= 1000) { cancelAssist(true); }
                return;
            }
            var candidates = assistCandidates(s, opts);
            if (!candidates.length || (!swapping && candidates.some(function (w) { return near(w.frameGeometry, s.target, 2); }))) {
                cancelAssist(true); return;
            }
            s.ready = true;
            s.candidates = candidates.slice(0, 50);
            sendAssist({ visible: true, session: s.session, action: s.action, geometry: s.popup,
                candidates: s.candidates.map(function (w) {
                    return { id: id(w), caption: String(w.caption || w.resourceClass || "Window").slice(0, 300),
                        application: String(w.desktopFileName || w.resourceClass || "").slice(0, 200) };
                }) });
            positionAssist();
        }

        function offerAssist(w, action, placed, output, area, opts) {
            cancelAssist(false);
            var opposite = { left: "right", right: "left", top: "bottom", bottom: "top" }[action];
            if (!assistTimer || !opts.snapAssist || !opposite) { return; }
            var target = zone(area, fractions(opposite, 0, false), opts.gap);
            if (target.width < 360 || target.height < 320) { return; }
            var width = Math.min(480, target.width - 32), height = Math.min(400, target.height - 32);
            assist = { source: w, session: String(now()) + ":" + (++assistSerial), created: now(),
                placed: rect(placed), output: name(output), area: rect(area), action: opposite,
                target: target, ready: false, focused: false, candidates: [],
                popup: { x: Math.round(target.x + (target.width - width) / 2),
                    y: Math.round(target.y + (target.height - height) / 2), width: width, height: height } };
            assistTimer.start(); updateAssist();
        }

        function assistCommand(command) {
            var s = assist;
            if (!s || command.session !== s.session) { return false; }
            if (!command.target) { cancelAssist(true); return true; }
            updateAssist();
            if (assist !== s || !s.ready) { return false; }
            var w = s.candidates.filter(function (candidate) { return id(candidate) === command.target; })[0];
            if (!w) { return false; }
            var output = findScreen(s.output), area = areaFor(output, w);
            if (!area || !near(area, s.area, 0)) { cancelAssist(true); return false; }
            cancelAssist(false);
            if (s.action === "swap") { return startSwap(s.source, w, output, area, command.token); }
            var before = rect(w.frameGeometry), mode = maxMode(w);
            var state = states[id(w)] || { original: { geometry: before, area: rect(area), output: name(output), mode: mode }, last: null };
            pairPlacement = { window: w, source: s.source, placed: s.placed, target: s.target, before: before,
                output: s.output, area: area, state: state, action: s.action, mode: mode, token: command.token, created: now() };
            assistTimer.start();
            place(w, s.target, output);
            checkPair();
            return null;
        }

        function swapEligible(w, opts) {
            return eligible(w, opts) && w.normalWindow && !w.dialog && currentContext(w) && tracked[id(w)] &&
                !maxMode(w) && !w.maximizedHorizontally && !w.maximizedVertically && !w.tile;
        }

        function offerSwap(w, output, area) {
            if (!assistTimer || !swapEligible(w, settings()) || area.width < 360 || area.height < 320 ||
                    !near(fit(w.frameGeometry, area), w.frameGeometry, 1)) { return false; }
            var width = Math.min(480, area.width - 32), height = Math.min(400, area.height - 32);
            assist = { source: w, session: String(now()) + ":" + (++assistSerial), created: now(),
                placed: rect(w.frameGeometry), output: name(output), area: rect(area), action: "swap",
                target: rect(w.frameGeometry), ready: false, focused: false, candidates: [],
                popup: { x: Math.round(area.x + (area.width - width) / 2),
                    y: Math.round(area.y + (area.height - height) / 2), width: width, height: height } };
            assistTimer.start(); updateAssist();
            return Boolean(assist);
        }

        function canUndoSwap(w) {
            var u = swapUndo, opts = settings();
            if (!u || swapPlacement || !u.entries.some(function (e) { return e.window === w; })) { return false; }
            var output = findScreen(u.output), area = output && areaFor(output, w);
            return Boolean(area && near(area, u.area, 0) && u.entries.every(function (e) {
                return swapEligible(e.window, opts) && name(screenFor(e.window)) === u.output &&
                    near(e.window.frameGeometry, e.after, 2) && fitsAssist(e.window, e.before);
            }));
        }

        function cancelSwap(rollback, removed) {
            var p = swapPlacement;
            if (!p) { return; }
            swapPlacement = null; assistTimer.stop();
            var output = findScreen(p.output), area = output && areaFor(output, p.entries[0].window);
            if (rollback && area && near(area, p.area, 0)) {
                p.entries.forEach(function (e) {
                    if (e.window !== removed && swapEligible(e.window, settings())) {
                        try { place(e.window, e.before, output); }
                        catch (error) { log("Swap rollback failed: " + String(error)); }
                    }
                });
            }
            publish({ token: p.token, success: false });
        }

        function checkSwap() {
            var p = swapPlacement;
            if (!p) { return; }
            var output = findScreen(p.output), area = output && areaFor(output, p.entries[0].window), opts = settings();
            var active = plasma5 ? ws.activeClient : ws.activeWindow;
            if (!area || !near(area, p.area, 0) ||
                    (active && !ownWindow(active) && !p.entries.some(function (e) { return e.window === active; })) ||
                    !p.entries.every(function (e) {
                        return swapEligible(e.window, opts) && name(screenFor(e.window)) === p.output && fitsAssist(e.window, e.target);
                    })) { cancelSwap(true); return; }
            if (!p.entries.every(function (e) { return near(e.window.frameGeometry, e.target, 2); })) {
                if (now() - p.created >= 1000) { cancelSwap(true); }
                return;
            }
            swapPlacement = null; assistTimer.stop();
            p.entries.forEach(function (e, i) {
                if (p.undo) {
                    var previous = p.undo.entries[i].previous;
                    if (previous) { states[id(e.window)] = previous; } else { delete states[id(e.window)]; }
                } else {
                    var state = states[id(e.window)] || { original: { geometry: e.before, area: rect(area), output: p.output, mode: 0 }, last: null };
                    states[id(e.window)] = state;
                    remember(state, "swap", 0, e.target, e.before, output, area);
                }
            });
            swapUndo = p.undo ? null : { output: p.output, area: p.area, entries: p.entries.map(function (e) {
                return { window: e.window, before: e.before, after: e.target, previous: e.previous };
            }) };
            lastWindow = p.focus;
            if (plasma5) { ws.activeClient = p.focus; } else { ws.activeWindow = p.focus; }
            publish({ token: p.token, success: true, operation: p.undo ? "undo-swap" : "swap" });
        }

        function startSwap(first, second, output, area, token, undo) {
            var windows = [first, second];
            var entries = windows.map(function (w, i) {
                return { window: w, before: rect(w.frameGeometry),
                    target: undo ? rect(undo.entries[i].before) : rect(windows[1 - i].frameGeometry),
                    previous: states[id(w)] ? JSON.parse(JSON.stringify(states[id(w)])) : null };
            });
            if (!entries.every(function (e) { return swapEligible(e.window, settings()) && fitsAssist(e.window, e.target); })) { return false; }
            swapPlacement = { entries: entries, output: name(output), area: rect(area), token: token,
                created: now(), undo: undo || null, focus: undo ? appTarget() || first : first };
            assistTimer.start();
            try {
                entries.forEach(function (e) { place(e.window, e.target, output); });
                checkSwap();
            } catch (error) { log("Swap failed: " + String(error)); cancelSwap(true); }
            return null;
        }

        function sendSnap(payload) {
            if (env.callDBus) {
                env.callDBus("org.krect.KRect", "/KRect", "org.krect.KRect", "SnapUpdate", JSON.stringify(payload));
            }
        }

        function hideSnap() {
            if (!drag || !drag.layout) { return; }
            if (drag.outlined && ws.hideOutline) { ws.hideOutline(); }
            drag.layout = null; drag.selected = -1; drag.outlined = false;
            sendSnap({ visible: false });
        }

        function cancelDrag() {
            pendingDrop = null;
            if (dropTimer) { dropTimer.stop(); }
            hideSnap(); drag = null;
            if (snapTimer) { snapTimer.stop(); }
        }

        function positionOverlay() {
            if (!overlay || !drag || !drag.layout) { return; }
            overlay.keepAbove = true; overlay.skipTaskbar = true; overlay.skipPager = true;
            overlay.noBorder = true;
            if (!near(overlay.frameGeometry, drag.layout.geometry, 1)) {
                overlay.frameGeometry = rect(drag.layout.geometry);
            }
            // Plasma 6 can raise Wayland windows without activating them.
            if (typeof ws.raiseWindow === "function") { ws.raiseWindow(overlay); }
        }

        function updateDrag() {
            if (!drag || updatingDrag) { return; }
            updatingDrag = true;
            try {
                var opts = settings(), w = drag.window;
                if (!w.move || !currentContext(w) || !eligible(w, opts, true) || !opts.snapBar) { cancelDrag(); return; }
                var pointer = ws.cursorPos;
                var output = screenList().filter(function (s) { return contains(s.geometry, pointer); })[0];
                var area = output && areaFor(output, w);
                if (!area || (name(output) !== name(screenFor(w)) && !w.moveableAcrossScreens)) { hideSnap(); return; }
                var layout = snapLayout(area, opts.portrait && area.height > area.width);
                if (!layout) { hideSnap(); return; }
                var g = layout.geometry;
                var top = Math.min(area.y, output.geometry.y);
                var activation = { x: g.x, y: top, width: g.width, height: area.y + 28 - top };
                var retention = { x: g.x - 32, y: Math.min(area.y, output.geometry.y), width: g.width + 64,
                    height: g.y + g.height + 32 - Math.min(area.y, output.geometry.y) };
                var retained = drag.layout && drag.output === name(output) && contains(retention, pointer);
                if (!retained && !contains(activation, pointer)) { hideSnap(); return; }
                var changed = !drag.layout || drag.output !== name(output) || !near(drag.layout.geometry, g, 0);
                drag.layout = layout; drag.output = name(output); drag.area = area;
                positionOverlay();
                var selected = -1;
                if (overlay && !overlay.deleted && !overlay.minimized && near(overlay.frameGeometry, g, 1)) {
                    var local = { x: pointer.x - g.x, y: pointer.y - g.y };
                    layout.cells.some(function (cell, i) {
                        if (contains(cell.rect, local)) { selected = i; return true; }
                        return false;
                    });
                }
                changed = changed || selected !== drag.selected;
                drag.selected = selected;
                if (selected !== -1 && ws.showOutline) {
                    var target = zone(area, fractions(layout.cells[selected].action, 0, opts.portrait && area.height > area.width), opts.gap);
                    ws.showOutline(target.x, target.y, target.width, target.height);
                    drag.outlined = true;
                } else if (drag.outlined && ws.hideOutline) {
                    ws.hideOutline(); drag.outlined = false;
                }
                if (changed || now() - drag.sent >= 500) {
                    sendSnap({ visible: true, geometry: g, cells: layout.cells, selected: selected });
                    drag.sent = now();
                }
            } catch (error) { log("Snap bar failed: " + String(error)); cancelDrag(); }
            finally { updatingDrag = false; }
        }

        function beginDrag(w) {
            cancelWorkspace();
            cancelPair(false);
            cancelSwap(true);
            if (swapUndo && swapUndo.entries.some(function (e) { return e.window === w; })) { swapUndo = null; }
            cancelAssist(false);
            cancelDrag();
            var opts = settings(), area = areaFor(screenFor(w), w);
            if (!snapTimer || !opts.snapBar || !w.move || !area || !currentContext(w) || !eligible(w, opts, true)) { return; }
            drag = { window: w, serial: ++dragSerial, selected: -1, sent: 0,
                original: { geometry: rect(tracked[id(w)].idleGeometry || w.frameGeometry), area: area,
                    output: name(screenFor(w)), mode: maxMode(w) } };
            snapTimer.start(); updateDrag();
        }

        function finishDrag(w) {
            var d = drag && drag.window === w ? drag : null;
            delete states[id(w)];
            if (!d) { return; }
            var cell = d.layout && d.layout.cells[d.selected];
            var g = d.layout && d.layout.geometry, p = ws.cursorPos;
            var selected = cell && contains(cell.rect, { x: p.x - g.x, y: p.y - g.y });
            cancelDrag();
            if (selected) {
                pendingDrop = { drag: d, action: cell.action };
                // KWin emits Finished inside a geometry-update blocker. Wait for
                // cancellation/native tiling to settle before observing the frame.
                dropTimer.start();
            }
            publish();
        }

        function applyDrop() {
            var pending = pendingDrop; pendingDrop = null;
            if (!pending) { return; }
            var d = pending.drag, w = d.window, opts = settings();
            if (!tracked[id(w)] || d.serial !== dragSerial || !opts.snapBar || !currentContext(w) || !eligible(w, opts)) { return; }
            // Both supported KWin APIs restore the initial frame on Esc, but do
            // not expose the cancel flag to scripts. Be conservative on a no-op.
            if (near(w.frameGeometry, d.original.geometry, 2) || maxMode(w) || w.tile) { return; }
            var output = findScreen(d.output), area = output && areaFor(output, w);
            if (!area || !near(area, d.area, 0)) { return; }
            var before = rect(w.frameGeometry);
            var target = zone(area, fractions(pending.action, 0, opts.portrait && area.height > area.width), opts.gap);
            var state = { original: d.original, last: null };
            states[id(w)] = state;
            place(w, target, output);
            remember(state, pending.action, 0, target, before, output, area);
            offerAssist(w, pending.action, target, output, area, opts);
            publish();
        }

        if (snapTimer) {
            workspaceTimer.interval = 100;
            workspaceTimer.timeout.connect(function () {
                try { checkWorkspace(); } catch (error) { log("Workspace restore failed: " + String(error)); cancelWorkspace(); }
            });
            snapTimer.interval = 50;
            snapTimer.timeout.connect(updateDrag);
            dropTimer.singleShot = true; dropTimer.interval = 0;
            dropTimer.timeout.connect(function () {
                try { applyDrop(); } catch (error) { log("Snap drop failed: " + String(error)); }
            });
            assistTimer.interval = 200;
            assistTimer.timeout.connect(function () {
                try { checkPair(); checkSwap(); updateAssist(); }
                catch (error) { log("Window chooser failed: " + String(error)); cancelPair(true); cancelSwap(true); cancelAssist(true); }
            });
        }

        function watch(w) {
            var key = id(w);
            if (tracked[key]) { return; }
            tracked[key] = { mode: typeof w.maximizeMode === "number" ? w.maximizeMode : null,
                idleGeometry: valid(w.frameGeometry) ? rect(w.frameGeometry) : null };
            // Qt appends the application display name to native window titles.
            if (ownWindow(w) && /^KRect Snap Bar(?: — KRect)?$/.test(String(w.caption))) { overlay = w; positionOverlay(); }
            if (ownWindow(w) && /^KRect Fill Space(?: — KRect)?$/.test(String(w.caption))) {
                assistWindow = w;
                if (assist) { delete assist.closedAt; }
                positionAssist();
            }
            if (w.frameGeometryChanged && env.callDBus) {
                w.frameGeometryChanged.connect(function () {
                    if (tracked[key] && !w.move && !w.resize) { tracked[key].idleGeometry = rect(w.frameGeometry); }
                    if (lastWindow === w && !w.move && !w.resize) { publish(); }
                });
            }
            if (w.maximizedAboutToChange) {
                w.maximizedAboutToChange.connect(function (mode) {
                    if (tracked[key]) { tracked[key].mode = Number(mode); }
                });
            } else if (!ws.clientMaximizeSet && w.clientMaximizedStateAboutToChange) {
                w.clientMaximizedStateAboutToChange.connect(function (client, mode) {
                    if (tracked[key]) { tracked[key].mode = Number(mode); }
                });
            }
            var moveFinished = w.interactiveMoveResizeFinished || w.clientFinishUserMovedResized;
            if (moveFinished) {
                moveFinished.connect(function () { finishDrag(w); });
            }
            var moveStarted = w.interactiveMoveResizeStarted || w.clientStartUserMovedResized;
            var moveStepped = w.interactiveMoveResizeStepped || w.clientStepUserMovedResized;
            if (moveStarted) { moveStarted.connect(function () { beginDrag(w); }); }
            if (moveStepped) { moveStepped.connect(updateDrag); }
        }

        function maxMode(w) {
            return typeof w.maximizeMode === "number" ? w.maximizeMode : tracked[id(w)].mode;
        }

        function saveOriginal(w, area) {
            var key = id(w);
            if (!states[key]) {
                states[key] = {
                    original: { geometry: rect(w.frameGeometry), area: rect(area), output: name(screenFor(w)), mode: maxMode(w) },
                    last: null
                };
            }
            return states[key];
        }

        // KWin performs Wayland configure/ack asynchronously. Never loop until
        // the client accepts a size; client size constraints remain authoritative.
        function detachTile(w) {
            var tile = w.tile;
            if (!tile) { return; }
            // Plasma 6.4+ exposes unmanage(); the writable property remains the
            // compatibility path for early Plasma 6.
            if (typeof tile.unmanage === "function") { tile.unmanage(w); }
            else { w.tile = null; }
        }

        function place(w, geometry, output) {
            w.setMaximize(false, false);
            detachTile(w);
            if (output && name(output) !== name(screenFor(w))) {
                ws.sendClientToScreen(w, plasma5 ? output.index : output);
            }
            w.frameGeometry = rect(geometry);
        }

        function remember(state, action, index, geometry, before, output, area) {
            state.last = { action: action, index: index, geometry: rect(geometry), before: rect(before),
                output: name(output), area: rect(area), time: now() };
        }

        function matchesLast(w, last) {
            return last && (near(w.frameGeometry, last.geometry, 2) ||
                (now() - last.time < 250 && near(w.frameGeometry, last.before, 2)));
        }

        function execute(action, explicitWindow, token) {
            var opts = settings();
            var w = explicitWindow || (plasma5 ? ws.activeClient : ws.activeWindow);
            if (!eligible(w, opts)) { return false; }
            watch(w);
            var output = screenFor(w);
            var area = areaFor(output, w);
            if (!area) { return false; }
            var key = id(w), state = states[key], target, before, last, dest;

            if (action === "swap") { return offerSwap(w, output, area); }
            if (action === "undo-swap") {
                if (!canUndoSwap(w)) { return false; }
                return startSwap(swapUndo.entries[0].window, swapUndo.entries[1].window, output, area, token, swapUndo);
            }
            if (swapUndo && swapUndo.entries.some(function (e) { return e.window === w; })) { swapUndo = null; }

            if (action === "restore") {
                if (!state) { return false; }
                var original = state.original;
                var originalDesktop = original.desktop ? findDesktop(original.desktop) : null;
                if (original.desktop && !originalDesktop) { return false; }
                dest = findScreen(original.output) || output;
                var restoreArea = areaFor(dest, w, originalDesktop ? originalDesktop.value : undefined);
                if (!restoreArea) { return false; }
                target = near(restoreArea, original.area, 0) ? fit(original.geometry, restoreArea) :
                    mapRect(original.geometry, original.area, restoreArea);
                if (originalDesktop) { setDesktop(w, originalDesktop); }
                place(w, target, dest);
                if (typeof original.mode === "number" && original.mode !== 0) {
                    // KWin MaximizeVertical = 1; MaximizeHorizontal = 2.
                    w.setMaximize(Boolean(original.mode & 1), Boolean(original.mode & 2));
                }
                delete states[key];
                return true;
            }

            if (action === "next-screen" || action === "previous-screen") {
                var screens = screenList();
                if (screens.length < 2 || !w.moveableAcrossScreens) { return false; }
                state = saveOriginal(w, area);
                last = state.last;
                var matched = matchesLast(w, last);
                var sourceName = matched ? last.output : name(output);
                var at = screens.map(name).indexOf(sourceName);
                if (at === -1) { return false; }
                dest = screens[(at + (action === "next-screen" ? 1 : screens.length - 1)) % screens.length];
                var destArea = areaFor(dest, w);
                if (!destArea) { return false; }
                before = rect(w.frameGeometry);
                var sourceGeometry = matched ? last.geometry : before;
                var sourceArea = matched ? last.area : area;
                var sourceAction = matched ? last.action : "move";
                var f = fractions(sourceAction, matched ? last.index : 0, opts.portrait && destArea.height > destArea.width);
                target = f ? zone(destArea, f, opts.gap) : mapRect(sourceGeometry, sourceArea, destArea);
                var mode = maxMode(w);
                place(w, target, dest);
                if (mode) { w.setMaximize(Boolean(mode & 1), Boolean(mode & 2)); }
                remember(state, sourceAction, matched ? last.index : 0, target, before, dest, destArea);
                return true;
            }

            if (action === "maximize") {
                if (!w.maximizable) { return false; }
                state = saveOriginal(w, area);
                before = rect(w.frameGeometry);
                detachTile(w);
                w.setMaximize(true, true);
                remember(state, action, 0, area, before, output, area);
                return true;
            }

            if (action === "center") {
                state = saveOriginal(w, area);
                before = rect(w.frameGeometry);
                var inner = zone(area, [0, 0, 1, 1], opts.gap);
                var size = fit(before, inner);
                target = { x: Math.round(inner.x + (inner.width - size.width) / 2),
                    y: Math.round(inner.y + (inner.height - size.height) / 2), width: size.width, height: size.height };
                place(w, target, output);
                remember(state, action, 0, target, before, output, area);
                return true;
            }

            if (!fractions(action, 0, false)) { return false; }
            state = saveOriginal(w, area);
            last = state.last;
            var index = 0;
            if (opts.cycle && ["left", "right", "top", "bottom"].indexOf(action) !== -1 && last &&
                    last.action === action && last.output === name(output) && near(last.area, area, 0) &&
                    now() - last.time < opts.timeout && matchesLast(w, last)) {
                index = (last.index + 1) % 3;
            }
            before = rect(w.frameGeometry);
            target = zone(area, fractions(action, index, opts.portrait && area.height > area.width), opts.gap);
            place(w, target, output);
            remember(state, action, index, target, before, output, area);
            return true;
        }

        function safeExecute(action, w, token) {
            cancelWorkspace();
            cancelPair(true);
            cancelSwap(true);
            cancelAssist(true);
            try { var result = execute(action, w, token); publish(); return result; }
            catch (error) { log(action + " failed: " + String(error)); return false; }
        }

        var removed = ws.windowRemoved || ws.clientRemoved;
        var added = ws.windowAdded || ws.clientAdded;
        if (removed) {
            removed.connect(function (w) {
                if (swapPlacement && swapPlacement.entries.some(function (e) { return e.window === w; })) { cancelSwap(true, w); }
                if (swapUndo && swapUndo.entries.some(function (e) { return e.window === w; })) { swapUndo = null; }
                if (pairPlacement && (pairPlacement.window === w || pairPlacement.source === w)) { cancelPair(pairPlacement.source === w); }
                if ((drag && drag.window === w) || (pendingDrop && pendingDrop.drag.window === w)) { cancelDrag(); }
                if (overlay === w) { overlay = null; if (drag) { hideSnap(); } }
                if (assist && assist.source === w) { cancelAssist(false); }
                // The chooser hides before its asynchronous D-Bus selection arrives.
                if (assist && assistWindow === w) { assist.closedAt = now(); }
                if (assistWindow === w) { assistWindow = null; }
                delete states[id(w)]; delete tracked[id(w)];
                if (lastWindow === w) { lastWindow = null; publish(); }
            });
        }
        if (added) { added.connect(watch); }
        Array.prototype.forEach.call(plasma5 ? ws.clientList() : (ws.stackingOrder || []), watch);
        if (plasma5 && ws.clientMaximizeSet) {
            ws.clientMaximizeSet.connect(function (w, horizontal, vertical) {
                if (tracked[id(w)]) { tracked[id(w)].mode = Number(vertical) + 2 * Number(horizontal); }
            });
        }
        var activation = ws.windowActivated || ws.clientActivated;
        if (activation) { activation.connect(activated); }
        [ws.currentDesktopChanged, ws.currentActivityChanged, ws.screensChanged, ws.numberScreensChanged].forEach(function (signal) {
            if (signal && env.callDBus) { signal.connect(function () { cancelDrag(); cancelPair(true); cancelSwap(true); swapUndo = null; cancelAssist(false); publish(); }); }
        });
        if (ws.cursorPosChanged && snapTimer) { ws.cursorPosChanged.connect(updateDrag); }
        activated(plasma5 ? ws.activeClient : ws.activeWindow);

        ACTIONS.forEach(function (action) {
            if (env.registerShortcut("KRect-" + action[0], "KRect: " + action[1], action[2], function () {
                safeExecute(action[0]);
            }) === false) { log("Could not register shortcut: " + action[0]); }
        });
        if (env.callDBus) {
            env.registerShortcut("KRect-app-command", "KRect: Desktop app connection", "", appCommand);
        }

        if (env.registerUserActionsMenu) {
            env.registerUserActionsMenu(function (w) {
                if (!eligible(w, settings())) { return undefined; }
                return { text: "KRect", items: ACTIONS.map(function (action) {
                    return { text: action[1], triggered: function () { safeExecute(action[0], w); } };
                }) };
            });
        }

        return { execute: safeExecute };
    }

    return { start: start, actions: ACTIONS, rect: rect, zone: zone, fractions: fractions, mapRect: mapRect, near: near,
        snapLayout: snapLayout };
}));
