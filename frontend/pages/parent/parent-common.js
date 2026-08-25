/* ChemAI 家长端 — 公共基础层（零构建，各页通过 <script src="parent-common.js"> 引入）
 *
 * 子系统：
 * 1. ChemAPI  — 请求封装、JWT 管理、认证守卫
 * 2. ChemUI   — Toast、骨架屏、数字动画、共享样式
 */
(function (window) {
  'use strict';

  var TOKEN_KEY = 'chemai_parent_token';
  var API_BASE = window.ChemAPI_BASE || 'http://localhost:8000';

  /* ═══════════════════════════════════════════════════════════════
   * 1. ChemAPI — 请求 & 认证
   * ═══════════════════════════════════════════════════════════════ */

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setToken(token) {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  function decodeJwt(token) {
    var parts = (token || '').split('.');
    if (parts.length < 2) return null;
    var b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    var pad = b64 + '===='.slice((b64.length % 4) || 4);
    try {
      var bin = atob(pad);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return JSON.parse(new TextDecoder().decode(bytes));
    } catch (e) {
      return null;
    }
  }

  function parentId() {
    var p = decodeJwt(getToken());
    return (p && p.entity_id) || null;
  }

  function role() {
    var p = decodeJwt(getToken());
    return (p && p.role) || null;
  }

  function _redirectToLogin() {
    setToken('');
    window.location.href = 'parent-login.html';
  }

  function isTokenValid() {
    var token = getToken();
    if (!token) return false;
    var payload = decodeJwt(token);
    if (!payload || !payload.exp) return false;
    return Date.now() < payload.exp * 1000;
  }

  function authGuard() {
    if (!isTokenValid()) {
      _redirectToLogin();
      return false;
    }
    return true;
  }

  function logout() {
    _redirectToLogin();
  }

  function api(path, options) {
    options = options || {};
    options.headers = Object.assign(
      { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
      options.headers || {}
    );
    return fetch(API_BASE + path, options).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (body) {
        if (!res.ok) {
          var d = body && body.detail;
          var msg = typeof d === 'string' ? d : (d && d.detail) || ('请求失败 (' + res.status + ')');
          var err = new Error(msg);
          err.status = res.status;
          if (res.status === 401 || res.status === 403) {
            _redirectToLogin();
          }
          throw err;
        }
        return body;
      });
    });
  }

  window.ChemAPI = {
    getToken: getToken,
    setToken: setToken,
    parentId: parentId,
    role: role,
    isTokenValid: isTokenValid,
    authGuard: authGuard,
    logout: logout,
    api: api,
    get: function (path) { return api(path); },
    post: function (path, data) { return api(path, { method: 'POST', body: JSON.stringify(data || {}) }); },
    put: function (path, data) { return api(path, { method: 'PUT', body: JSON.stringify(data || {}) }); },
    del: function (path) { return api(path, { method: 'DELETE' }); },
  };

  /* ═══════════════════════════════════════════════════════════════
   * 2. ChemUI — 界面组件
   * ═══════════════════════════════════════════════════════════════ */

  var _stylesInjected = false;
  function _injectSharedStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    var css = [
      '@keyframes skeleton-pulse { 0%,100%{opacity:.4} 50%{opacity:.7} }',
      '.skeleton{background:#e5e7eb;border-radius:6px;animation:skeleton-pulse 1.5s ease infinite}',
      '@keyframes card-in{from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)}}',
      '.card-animate{animation:card-in .4s ease both}',
    ].join('\n');
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function showToast(msg, type) {
    _injectSharedStyles();
    type = type || 'info';
    var colors = { success: '#2c6e49', error: '#b43c28', info: '#002147' };
    var el = document.createElement('div');
    el.textContent = msg;
    Object.assign(el.style, {
      position: 'fixed', top: '64px', left: '50%', transform: 'translateX(-50%)',
      zIndex: '100', background: colors[type] || colors.info, color: '#fff',
      padding: '8px 20px', borderRadius: '8px', fontSize: '13px',
      fontFamily: '"IBM Plex Sans","Noto Sans SC",sans-serif',
      boxShadow: '0 2px 8px rgba(0,0,0,.15)', opacity: '0',
      transition: 'opacity .25s',
    });
    document.body.appendChild(el);
    requestAnimationFrame(function () { el.style.opacity = '1'; });
    setTimeout(function () {
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 300);
    }, 2500);
  }

  function fmtTime(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return (d.getMonth() + 1) + '月' + d.getDate() + '日 ' +
      d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
  }

  function fmtDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return (d.getMonth() + 1) + '月' + d.getDate() + '日';
  }

  function animateNumber(el, target, duration) {
    if (!el || target <= 0) { if (el) el.textContent = '0'; return; }
    duration = duration || 600;
    var start = performance.now();
    function tick(now) {
      var progress = Math.min((now - start) / duration, 1);
      var ease = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(ease * target);
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ═══════════════════════════════════════════════════════════════
   * 3. SSE 客户端
   * ═══════════════════════════════════════════════════════════════ */

  function createSSEClient(opts) {
    var controller = new AbortController();
    var closed = false;

    function close() {
      if (!closed) { closed = true; controller.abort(); }
    }

    var headers = Object.assign(
      { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
      opts.headers || {}
    );
    var body = opts.body;
    if (body && typeof body === 'object') body = JSON.stringify(body);

    fetch(API_BASE + opts.url, {
      method: opts.method || 'POST',
      headers: headers,
      body: body,
      signal: controller.signal,
    }).then(function (res) {
      if (!res.ok) {
        return res.json().catch(function () { return null; }).then(function (b) {
          var msg = (b && b.detail) || ('SSE 连接失败 (' + res.status + ')');
          throw new Error(msg);
        });
      }
      if (opts.onOpen) opts.onOpen();

      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      function pump() {
        return reader.read().then(function (result) {
          if (result.done) {
            if (opts.onDone) opts.onDone();
            return;
          }
          buffer += decoder.decode(result.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line || line.indexOf('event:') === 0) continue;
            if (line.indexOf('data:') === 0) {
              var dataStr = line.slice(5).trim();
              if (dataStr === '[DONE]') {
                if (opts.onDone) opts.onDone();
                return;
              }
              if (opts.onMessage) opts.onMessage(dataStr);
            }
          }
          return pump();
        });
      }

      return pump();
    }).catch(function (err) {
      if (err.name === 'AbortError') return;
      if (opts.onError) opts.onError(err);
    });

    return { close: close };
  }

  /* ═══════════════════════════════════════════════════════════════
   * 导出
   * ═══════════════════════════════════════════════════════════════ */

  window.ChemUI = {
    showToast: showToast,
    fmtTime: fmtTime,
    fmtDate: fmtDate,
    animateNumber: animateNumber,
    createSSEClient: createSSEClient,
  };

})(window);
