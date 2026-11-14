/* SPDX-License-Identifier: MIT
 * KRect 0.2.0 — window placement for KWin / Plasma 5.27 and 6.
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

    function start(env) {
        var ws = env.workspace;
        var plasma5 = typeof ws.screens === "undefined";
        var states = Object.create(null);
        var tracked = Object.create(null);
        var now = env.now || function () { return Date.now(); };
        var cfg = env.readConfig;
        var lastWindow = null;

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
            var status = { protocol: 1, version: "0.2.0", target: w ? {
                id: id(w), caption: String(w.caption || w.resourceClass || "Window"),
                application: String(w.desktopFileName || w.resourceClass || ""),
                geometry: rect(w.frameGeometry), area: areaFor(output, w), screen: name(output),
                canRestore: Boolean(states[id(w)]), maximizable: Boolean(w.maximizable),
                movableAcrossScreens: Boolean(w.moveableAcrossScreens)
            } : null, screens: screenList().map(function (screen) {
                return { name: name(screen), geometry: rect(screen.geometry), area: areaFor(screen, w) };
            }), result: result || null };
            env.callDBus("org.krect.KRect", "/KRect", "org.krect.KRect", "Update", JSON.stringify(status));
        }

        function activated(w) {
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
                    var w = appTarget();
                    var known = ACTIONS.some(function (a) { return a[0] === command.action; });
                    var success = Boolean(known && w && id(w) === command.target && safeExecute(command.action, w));
                    publish({ token: command.token, success: success });
                } catch (error) { log("Desktop app command failed: " + String(error)); publish(); }
            });
        }

        function settings() {
            return {
                gap: bounded(cfg("Gap", 8), 8, 0, 64),
                cycle: boolean(cfg("CycleHalves", true)),
                timeout: bounded(cfg("CycleTimeout", 1200), 1200, 200, 5000),
                portrait: boolean(cfg("PortraitThirds", true)),
                ignored: String(cfg("IgnoredApplications", "")).toLowerCase().split(/[,;\n]/).map(function (s) { return s.trim(); }).filter(Boolean)
            };
        }

        function id(w) { return String(w.internalId); }
        function name(output) { return output ? String(output.name) : ""; }
        function log(message) { if (env.log) { env.log(message); } }

        function eligible(w, opts) {
            if (!w || ownWindow(w) || w.deleted || !w.managed || !(w.normalWindow || w.dialog) ||
                    w.fullScreen || w.specialWindow || w.minimized || w.shade || w.move || w.resize ||
                    !w.moveable || !w.resizeable || !valid(w.frameGeometry)) {
                return false;
            }
            var identifiers = [w.resourceClass, w.resourceName, w.desktopFileName].map(function (s) {
                return String(s || "").toLowerCase();
            });
            return !opts.ignored.some(function (s) { return identifiers.indexOf(s) !== -1; });
        }

        function areaFor(output, w) {
            var area = output ? ws.clientArea(env.KWin.MaximizeArea, plasma5 ? output.index : output, ws.currentDesktop) :
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

        function watch(w) {
            var key = id(w);
            if (tracked[key]) { return; }
            tracked[key] = { mode: typeof w.maximizeMode === "number" ? w.maximizeMode : null };
            if (w.frameGeometryChanged && env.callDBus) {
                w.frameGeometryChanged.connect(function () { if (lastWindow === w) { publish(); } });
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
                moveFinished.connect(function () { delete states[key]; });
            }
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
            w.frameGeometry = geometry;
        }

        function remember(state, action, index, geometry, before, output, area) {
            state.last = { action: action, index: index, geometry: rect(geometry), before: rect(before),
                output: name(output), area: rect(area), time: now() };
        }

        function matchesLast(w, last) {
            return last && (near(w.frameGeometry, last.geometry, 2) ||
                (now() - last.time < 250 && near(w.frameGeometry, last.before, 2)));
        }

        function execute(action, explicitWindow) {
            var opts = settings();
            var w = explicitWindow || (plasma5 ? ws.activeClient : ws.activeWindow);
            if (!eligible(w, opts)) { return false; }
            watch(w);
            var output = screenFor(w);
            var area = areaFor(output, w);
            if (!area) { return false; }
            var key = id(w), state = states[key], target, before, last, dest;

            if (action === "restore") {
                if (!state) { return false; }
                var original = state.original;
                dest = findScreen(original.output) || output;
                var restoreArea = areaFor(dest, w);
                if (!restoreArea) { return false; }
                target = near(restoreArea, original.area, 0) ? fit(original.geometry, restoreArea) :
                    mapRect(original.geometry, original.area, restoreArea);
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

        function safeExecute(action, w) {
            try { var result = execute(action, w); publish(); return result; }
            catch (error) { log(action + " failed: " + String(error)); return false; }
        }

        var removed = ws.windowRemoved || ws.clientRemoved;
        var added = ws.windowAdded || ws.clientAdded;
        if (removed) {
            removed.connect(function (w) {
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
            if (signal && env.callDBus) { signal.connect(function () { publish(); }); }
        });
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

    return { start: start, actions: ACTIONS, rect: rect, zone: zone, fractions: fractions, mapRect: mapRect, near: near };
}));
