/* ChemAI 学生端 — 公共基础层（零构建，各页通过 <script src="common.js"> 引入）
 *
 * 子系统：
 * 1. ChemAPI  — 请求封装、JWT 管理、认证守卫
 * 2. ChemUI   — TabBar、Toast、Markdown 渲染、SSE 客户端
 */
(function (window) {
  'use strict';

  var TOKEN_KEY = 'chemai_token';
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

  function studentId() {
    var p = decodeJwt(getToken());
    return (p && p.entity_id) || null;
  }

  function role() {
    var p = decodeJwt(getToken());
    return (p && p.role) || null;
  }

  /** 检查 token 是否有效（存在 + 未过期），无效返回 false */
  function isTokenValid() {
    var token = getToken();
    if (!token) return false;
    var payload = decodeJwt(token);
    if (!payload || !payload.exp) return false;
    // exp 是秒级 Unix 时间戳
    return Date.now() < payload.exp * 1000;
  }

  /** 认证守卫：无 token 或过期则跳转 login.html */
  function authGuard() {
    if (!isTokenValid()) {
      setToken('');
      window.location.href = 'login.html';
      return false;
    }
    return true;
  }

  /** 退出登录：清除 token 并跳转登录页 */
  function logout() {
    setToken('');
    window.location.href = 'login.html';
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
          // 401/403 自动跳转登录
          if (res.status === 401 || res.status === 403) {
            setToken('');
            window.location.href = 'login.html';
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
    studentId: studentId,
    role: role,
    isTokenValid: isTokenValid,
    authGuard: authGuard,
    logout: logout,
    api: api,
    get: function (path) { return api(path); },
    post: function (path, data) { return api(path, { method: 'POST', body: JSON.stringify(data || {}) }); },
  };

  /* ═══════════════════════════════════════════════════════════════
   * 2. ChemUI — 界面组件
   * ═══════════════════════════════════════════════════════════════ */

  var TABS = [
    { id: 'ai',     icon: 'smart_toy',  label: 'AI助教', href: 'index.html' },
    { id: 'practice', icon: 'edit_note', label: '练习',   href: 'practice.html' },
    { id: 'wrong',  icon: 'fact_check',  label: '错题',   href: 'wrong.html' },
    { id: 'my',     icon: 'person',      label: '我的',   href: 'my.html' },
  ];

  /** 渲染底部 TabBar，active 为当前页 id（ai/practice/wrong/my） */
  function renderTabBar(active) {
    var nav = document.querySelector('.bottom-nav');
    if (!nav) return;
    nav.innerHTML = TABS.map(function (t) {
      var cls = t.id === active ? 'nav-item active' : 'nav-item';
      return '<a class="' + cls + '" href="' + t.href + '">'
        + '<span class="material-symbols-outlined">' + t.icon + '</span>'
        + '<span>' + t.label + '</span></a>';
    }).join('');
  }

  /** 轻量级 Toast 通知 */
  function showToast(msg, type) {
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

  /** 化学式 & Markdown 渲染：KaTeX auto-render + mhchem */
  function renderChemContent(el) {
    if (!el) return;
    if (window.renderMathInElement) {
      renderMathInElement(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
      });
    }
  }

  /* ═══════════════════════════════════════════════════════════════
   * 3. SSE 客户端（fetch + ReadableStream，支持 POST）
   * ═══════════════════════════════════════════════════════════════ */

  /**
   * 创建 SSE 客户端
   * @param {Object} opts
   * @param {string} opts.endpoint  - SSE 端点路径（如 /api/chat/langgraph/stream）
   * @param {Object} opts.body      - POST 请求体
   * @param {Function} opts.onEvent - (type: string, data: Object) => void
   * @param {Function} [opts.onError] - (error: Error) => void
   * @param {Function} [opts.onDone]  - () => void
   * @returns {{ close: Function, abort: Function }}
   */
  function createSSEClient(opts) {
    var controller = new AbortController();
    var closed = false;

    function close() {
      if (!closed) { closed = true; controller.abort(); }
    }

    fetch(API_BASE + opts.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getToken(),
      },
      body: JSON.stringify(opts.body || {}),
      signal: controller.signal,
    }).then(function (res) {
      if (!res.ok) {
        return res.json().catch(function () { return null; }).then(function (body) {
          var msg = (body && body.detail) || ('SSE 连接失败 (' + res.status + ')');
          throw new Error(msg);
        });
      }
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
          // SSE 格式：每条消息以 \n\n 分隔
          var lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 最后一行可能不完整，留在 buffer

          var eventType = '';
          for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (line.indexOf('event:') === 0) {
              eventType = line.slice(6).trim();
            } else if (line.indexOf('data:') === 0) {
              var dataStr = line.slice(5).trim();
              if (dataStr === '[DONE]') {
                if (opts.onDone) opts.onDone();
                return;
              }
              try {
                var data = JSON.parse(dataStr);
                if (opts.onEvent) opts.onEvent(eventType || 'message', data);
              } catch (e) {
                // 非 JSON data，忽略
              }
              eventType = '';
            }
          }
          return pump();
        });
      }

      return pump();
    }).catch(function (err) {
      if (err.name === 'AbortError') return; // 主动关闭
      if (opts.onError) opts.onError(err);
    });

    return { close: close, abort: close };
  }

  /* ═══════════════════════════════════════════════════════════════
   * 4. 数字跳动动画
   * ═══════════════════════════════════════════════════════════════ */

  /**
   * 数字从 0 跳动到 target
   * @param {HTMLElement} el - 显示数字的元素
   * @param {number} target - 目标数字
   * @param {number} [duration=600] - 动画时长 ms
   */
  function animateNumber(el, target, duration) {
    if (!el || target <= 0) { if (el) el.textContent = '0'; return; }
    duration = duration || 600;
    var start = performance.now();
    function tick(now) {
      var progress = Math.min((now - start) / duration, 1);
      // ease-out cubic
      var ease = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(ease * target);
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ═══════════════════════════════════════════════════════════════
   * 导出
   * ═══════════════════════════════════════════════════════════════ */

  window.ChemUI = {
    renderTabBar: renderTabBar,
    showToast: showToast,
    renderChemContent: renderChemContent,
    createSSEClient: createSSEClient,
    animateNumber: animateNumber,
  };

})(window);
