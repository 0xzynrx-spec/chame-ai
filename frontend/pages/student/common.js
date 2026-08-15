/* ChemAI 学生端 — 公共 API 工具（零构建，各页通过 <script src="common.js"> 引入）
 *
 * 约定：
 * - access token 存 localStorage（键 chemai_token）
 * - 学生 ID 取 JWT payload 的 entity_id（后端登录/me 不直接返回，需解码 token 读取）
 * - 所有请求经 api()/get()/post() 统一带鉴权头，非 2xx 抛 Error(detail)
 */
(function (window) {
  'use strict';

  var TOKEN_KEY = 'chemai_token';

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

  function studentId() {
    var p = decodeJwt(getToken());
    return (p && p.entity_id) || null;
  }

  function role() {
    var p = decodeJwt(getToken());
    return (p && p.role) || null;
  }

  // 统一请求封装：附加鉴权头，非 2xx 抛出带 detail 的 Error
  function api(path, options) {
    options = options || {};
    options.headers = Object.assign(
      { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
      options.headers || {}
    );
    return fetch(path, options).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (body) {
        if (!res.ok) {
          var d = body && body.detail;
          var msg = typeof d === 'string' ? d : (d && d.detail) || ('请求失败 (' + res.status + ')');
          var err = new Error(msg);
          err.status = res.status;
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
    api: api,
    get: function (path) { return api(path); },
    post: function (path, data) { return api(path, { method: 'POST', body: JSON.stringify(data || {}) }); },
  };
})(window);
