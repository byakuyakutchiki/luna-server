/**
 * LunaAuth — module d'authentification générique pour Luna.
 *
 * Responsabilités :
 *  - lecture / écriture des tokens dans localStorage
 *  - synchronisation avec le pont natif LunaBridge (APK)
 *  - refresh automatique du token d'accès
 *  - authFetch() avec retry silencieux sur 401
 *
 * Ce module est volontairement agnostique : aucune logique spécifique à Guardian.
 * Il peut être utilisé par n'importe quelle page de l'application (Guardian, Iris,
 * Documents, etc.).
 */
(function () {
  'use strict';

  var ACCESS_KEY = 'luna_token';
  var REFRESH_KEY = 'luna_refresh_token';

  var DEFAULT_LOGIN_URL = '/';

  function getAccessToken() {
    return localStorage.getItem(ACCESS_KEY) || '';
  }

  function getRefreshToken() {
    return localStorage.getItem(REFRESH_KEY) || '';
  }

  function setAccessToken(token) {
    if (token) {
      localStorage.setItem(ACCESS_KEY, token);
    } else {
      localStorage.removeItem(ACCESS_KEY);
    }
  }

  function setRefreshToken(token) {
    if (token) {
      localStorage.setItem(REFRESH_KEY, token);
    } else {
      localStorage.removeItem(REFRESH_KEY);
    }
  }

  function hasBridge() {
    return !!(window.LunaBridge);
  }

  // --- synchronisation native (APK uniquement) ---

  function syncFromNative() {
    if (!hasBridge() || !LunaBridge.getTokens) {
      return Promise.resolve(false);
    }
    try {
      var raw = LunaBridge.getTokens();
      var tokens = raw ? JSON.parse(raw) : {};
      if (tokens.access && !getAccessToken()) {
        setAccessToken(tokens.access);
      }
      if (tokens.refresh && !getRefreshToken()) {
        setRefreshToken(tokens.refresh);
      }
      return Promise.resolve(true);
    } catch (e) {
      return Promise.resolve(false);
    }
  }

  function syncToNative(access, refresh) {
    if (hasBridge() && LunaBridge.storeTokens) {
      try {
        LunaBridge.storeTokens(access || '', refresh || '');
      } catch (e) {
        // silencieux : le stockage natif est un meilleur effort
      }
    }
  }

  function clearNativeTokens() {
    if (hasBridge() && LunaBridge.clearTokens) {
      try {
        LunaBridge.clearTokens();
      } catch (e) {
        // silencieux
      }
    }
  }

  // --- refresh ---

  function refreshAccessToken() {
    var refresh = getRefreshToken();
    if (!refresh) {
      return Promise.resolve(false);
    }
    return fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh })
    }).then(function (r) {
      if (!r.ok) return false;
      return r.json().then(function (data) {
        if (!data.token) return false;
        setAccessToken(data.token);
        syncToNative(data.token, refresh);
        return true;
      });
    }).catch(function () {
      return false;
    });
  }

  // --- authFetch ---

  function authFetch(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign({}, opts.headers || {});
    var token = getAccessToken();
    if (token) {
      opts.headers['Authorization'] = 'Bearer ' + token;
    }

    return fetch(url, opts).then(function (r) {
      if (r.status !== 401) {
        return r;
      }

      return refreshAccessToken().then(function (ok) {
        if (!ok) {
          LunaAuth.clearTokens();
          LunaAuth.requiresLogin();
          throw new Error('session_expired');
        }
        opts.headers = Object.assign({}, opts.headers || {});
        opts.headers['Authorization'] = 'Bearer ' + getAccessToken();
        return fetch(url, opts);
      });
    });
  }

  // --- init ---

  function init() {
    return syncFromNative().then(function () {
      return !!getAccessToken();
    });
  }

  // --- exposition publique ---

  window.LunaAuth = {
    getToken: getAccessToken,
    getRefreshToken: getRefreshToken,
    setTokens: function (access, refresh) {
      setAccessToken(access);
      setRefreshToken(refresh);
      syncToNative(access, refresh);
    },
    clearTokens: function () {
      setAccessToken('');
      setRefreshToken('');
      clearNativeTokens();
    },
    refreshAccessToken: refreshAccessToken,
    authFetch: authFetch,
    init: init,
    requiresLogin: function () {
      window.location.href = DEFAULT_LOGIN_URL;
    },
    setLoginUrl: function (url) {
      DEFAULT_LOGIN_URL = url || '/';
    }
  };
})();
