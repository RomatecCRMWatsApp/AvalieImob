import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { authAPI } from '../lib/api';

const AuthContext = createContext(null);

// NOTE: Storing JWT in localStorage is acceptable for this MVP.
// For production with higher security requirements, migrate to httpOnly cookies
// (requires CSRF protection + backend cookie config).
const TOKEN_KEY = 'romatec_token';
const USER_KEY = 'romatec_user';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const stored = localStorage.getItem(USER_KEY);
    if (token && stored) {
      try {
        setUser(JSON.parse(stored));
      } catch (err) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('Failed to parse stored user', err);
        }
      }
      // Validate token in background
      authAPI.me()
        .then((u) => {
          setUser(u);
          localStorage.setItem(USER_KEY, JSON.stringify(u));
        })
        .catch((err) => {
          if (process.env.NODE_ENV === 'development') {
            console.warn('Token validation failed, clearing session', err?.response?.status);
          }
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await authAPI.login({ email, password });
    localStorage.setItem(TOKEN_KEY, res.token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  }, []);

  const register = useCallback(async (data) => {
    const res = await authAPI.register(data);
    localStorage.setItem(TOKEN_KEY, res.token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const u = await authAPI.me();
      setUser(u);
      localStorage.setItem(USER_KEY, JSON.stringify(u));
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.warn('Failed to refresh user', err);
      }
    }
  }, []);

  const value = useMemo(
    () => ({ user, login, register, logout, loading, refreshUser }),
    [user, login, register, logout, loading, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
};
