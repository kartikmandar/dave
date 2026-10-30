/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 DAVE contributors. See the repository LICENSE.
 * Original DAVE log-panel implementation; legacy global names are compatibility APIs.
 */
(function (root) {
  'use strict';
  const height = 215;
  let panel, tab, output, motion;
  let visible = true, enabled = true, expanded = false, rowLimit = 0;
  const pad = value => String(value).padStart(2, '0');
  const clock = date => [date.getHours(), date.getMinutes(), date.getSeconds()].map(pad).join(':');

  function initialize() {
    if (panel && panel.isConnected) return true;
    if (!document.body) return false;
    panel = document.getElementById('loggerContainer') || document.createElement('div');
    panel.id = 'loggerContainer';
    tab = panel.querySelector('#loggerTab') || document.createElement('div');
    tab.id = 'loggerTab';
    tab.textContent = 'LOG';
    tab.style.lineHeight = '19px';
    tab.style.top = '-20px';
    tab.tabIndex = 0;
    tab.setAttribute('role', 'button');
    tab.setAttribute('aria-controls', 'logger');
    tab.setAttribute('aria-expanded', String(expanded));
    tab.onclick = () => api.toggle();
    tab.onkeydown = event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        api.toggle();
      }
    };
    output = panel.querySelector('#logger') || document.createElement('div');
    output.id = 'logger';
    output.style.height = height + 'px';
    output.style.visibility = expanded ? 'visible' : 'hidden';
    output.setAttribute('role', 'log');
    if (!output.hasChildNodes()) {
      const now = new Date();
      const banner = document.createElement('span');
      banner.style.color = '#afa';
      banner.style.fontWeight = 'bold';
      banner.textContent = '===== DAVE Started at ' + [now.getFullYear(), pad(now.getMonth() + 1), pad(now.getDate())].join('-') + ', ' + clock(now) + ', =====';
      output.append(banner, document.createElement('br'), document.createElement('br'));
    }
    panel.append(tab, output);
    panel.style.bottom = (expanded ? 0 : -height) + 'px';
    panel.style.display = visible ? 'block' : 'none';
    if (!panel.isConnected) document.body.append(panel);
    return true;
  }

  function trim() {
    if (!output || rowLimit <= 0) return;
    const rows = output.querySelectorAll('.loggerRow');
    for (let index = 0; index < rows.length - rowLimit; index++) rows[index].remove();
  }

  function reveal(next) {
    if (!initialize() || !visible || expanded === next) return;
    const previous = getComputedStyle(panel).bottom;
    if (motion) motion.cancel();
    expanded = next;
    tab.setAttribute('aria-expanded', String(next));
    output.style.visibility = 'visible';
    const bottom = (next ? 0 : -height) + 'px';
    panel.style.bottom = bottom;
    const animation = panel.animate([{ bottom: previous }, { bottom }], {
      duration: root.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 200,
      easing: 'cubic-bezier(0.37, 0, 0.63, 1)'
    });
    motion = animation;
    animation.finished.then(() => {
      if (motion !== animation) return;
      output.style.visibility = next ? 'visible' : 'hidden';
      motion = null;
    }).catch(() => {}); // A reverse toggle cancels the previous animation.
  }

  const api = {
    init: initialize,
    print(message, cssClass) {
      if (!enabled || !initialize()) return;
      const absent = message === undefined || message === null;
      for (const line of String(message).split(/\r\n|\r|\n/)) {
        const row = document.createElement('div');
        row.className = 'loggerRow';
        const time = document.createElement('div');
        time.className = 'loggerTime';
        time.textContent = clock(new Date()) + '\u00a0';
        const text = document.createElement('div');
        text.className = 'loggerMsg' + (cssClass == null ? '' : ' ' + String(cssClass));
        if (absent) text.style.color = '#afa';
        text.textContent = line.replace(/ /g, '\u00a0');
        row.append(time, text);
        output.append(row);
      }
      trim();
      output.scrollTop = output.scrollHeight;
    },
    toggle() { reveal(!expanded); },
    open() { reveal(true); },
    close() { reveal(false); },
    show() { visible = true; if (initialize()) panel.style.display = 'block'; },
    hide() { visible = false; if (initialize()) panel.style.display = 'none'; },
    enable() {
      enabled = true;
      if (initialize()) { tab.style.color = '#fff'; output.style.color = '#fff'; }
    },
    disable() {
      enabled = false;
      if (initialize()) { tab.style.color = '#444'; output.style.color = '#444'; }
    },
    clear() { if (initialize()) output.replaceChildren(); },
    setMaxRows(value) {
      const count = Number(value);
      rowLimit = Number.isFinite(count) && count > 0 ? Math.floor(count) : 0;
      trim();
    }
  };
  for (const [level, cssClass] of Object.entries({ debug: 'LogDebug', info: 'LogInfo', warn: 'LogWarn', error: 'LogError' })) {
    api[level] = (...messages) => api.print(messages.map(String).join(' '), cssClass);
  }
  root.Logger = api;
  root.log = function (message, cssClass) { api.print(arguments.length ? message : '', cssClass); };
  root.logDebug = message => api.print(message, 'LogDebug');
  root.logInfo = message => api.print(message, 'LogInfo');
  root.logWarn = message => api.print(message, 'LogWarn');
  root.logErr = message => api.print(message, 'LogError');
})(window);
