/* ChemAI 学生端 — 公共基础层（零构建，各页通过 <script src="common.js"> 引入）
 *
 * 子系统：
 * 1. ChemAPI  — 请求封装、JWT 管理、认证守卫
 * 2. ChemUI   — TabBar、Toast、Markdown 渲染、SSE 客户端、共享样式
 */
(function (window) {
  'use strict';

  // 后端 API 基地址（默认与 exam-v2 一致；异源部署时页面可先设 window.ChemAPI_BASE 覆盖）
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

  // 解码 JWT payload 段（base64url → JSON），不解签（服务端负责验签）
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

  // 从 JWT 中取学生 ID（entity_id 字段）
  function studentId() {
    var p = decodeJwt(getToken());
    return (p && p.entity_id) || null;
  }

  // 从 JWT 中取角色
  function role() {
    var p = decodeJwt(getToken());
    return (p && p.role) || null;
  }

  // 内部辅助：跳转登录页（统一处理清除 token + 重定向）
  function _redirectToLogin() {
    setToken('');
    window.location.href = 'login.html';
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
      _redirectToLogin();
      return false;
    }
    return true;
  }

  /** 退出登录：清除 token 并跳转登录页 */
  function logout() {
    _redirectToLogin();
  }

  // 统一请求封装：附加鉴权头，非 2xx 抛出带 detail 的 Error
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

  // 底部 Tab 配置
  var TABS = [
    { id: 'ai',     icon: 'smart_toy',  label: 'AI助教', href: 'index.html' },
    { id: 'practice', icon: 'edit_note', label: '练习',   href: 'practice.html' },
    { id: 'wrong',  icon: 'fact_check',  label: '错题',   href: 'wrong.html' },
    { id: 'my',     icon: 'person',      label: '我的',   href: 'my.html' },
  ];

  // 共享样式（骨架屏、卡片动画、底部导航），首次调用时注入 <head>
  var _stylesInjected = false;
  function _injectSharedStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    var css = [
      /* 骨架屏脉冲 */
      '@keyframes skeleton-pulse { 0%,100%{opacity:.4} 50%{opacity:.7} }',
      '.skeleton{background:#e5e7eb;border-radius:6px;animation:skeleton-pulse 1.5s ease infinite}',
      /* 卡片入场动画 */
      '@keyframes card-in{from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)}}',
      '.card-animate{animation:card-in .4s ease both}',
      /* 底部导航 */
      '.bottom-nav{position:fixed;bottom:0;left:0;right:0;margin:0 auto;max-width:430px;height:56px;display:flex;background:#fff;border-top:1px solid #eee;z-index:20}',
      '.nav-item{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;color:#8b8b9c;font-size:10px;text-decoration:none}',
      '.nav-item .material-symbols-outlined{font-size:22px}',
      '.nav-item.active{color:#002147}',
      '.nav-item.active span:last-child{font-weight:600}',
    ].join('\n');
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  /** 渲染底部 TabBar，active 为当前页 id（ai/practice/wrong/my） */
  function renderTabBar(active) {
    _injectSharedStyles();
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

  /** 格式化时间：ISO 字符串 → "M/D H:mm" */
  function fmtTime(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return (d.getMonth() + 1) + '/' + d.getDate() + ' ' +
      d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
  }

  /** 渲染 KaTeX 数学公式（需先引入 KaTeX 脚本） */
  function renderMath(el) {
    if (!el || !window.renderMathInElement) return;
    renderMathInElement(el, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
      ],
      throwOnError: false,
    });
  }

  /* ═══════════════════════════════════════════════════════════════
   * 3. SSE 客户端（fetch + ReadableStream，支持 POST）
   * ═══════════════════════════════════════════════════════════════ */

  /**
   * 创建 SSE 客户端
   * @param {Object} opts
   * @param {string} opts.url      - SSE 端点完整路径（如 /api/chat/langgraph/stream）
   * @param {string} [opts.method]  - HTTP 方法（默认 POST）
   * @param {Object} [opts.headers] - 额外请求头
   * @param {Object|string} [opts.body] - POST 请求体（对象会自动 JSON.stringify）
   * @param {Function} [opts.onOpen]    - 连接建立时回调
   * @param {Function} [opts.onMessage] - (data: string) => void，每收到一条 data 行触发
   * @param {Function} [opts.onError]   - (error: Error) => void
   * @param {Function} [opts.onDone]    - () => void，流结束或收到 [DONE]
   * @returns {{ close: Function }}
   */
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
          // SSE 格式：每条消息以 \n\n 分隔
          var lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 最后一行可能不完整，留在 buffer

          for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            // 跳过 event: 行（调用方通过 data 中的 event 字段区分）
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
      if (err.name === 'AbortError') return; // 主动关闭
      if (opts.onError) opts.onError(err);
    });

    return { close: close };
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
    renderMath: renderMath,
    createSSEClient: createSSEClient,
    animateNumber: animateNumber,
    fmtTime: fmtTime,
  };

})(window);
