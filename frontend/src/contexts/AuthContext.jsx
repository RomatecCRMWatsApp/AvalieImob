import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../lib/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('romatec_token');
    const stored = localStorage.getItem('romatec_user');
    if (token && stored) {
      try { setUser(JSON.parse(stored)); } catch { /* noop */ }
      // validate token in background
      authAPI.me().then((u) => {
        setUser(u);
        localStorage.setItem('romatec_user', JSON.stringify(u));
      }).catch(() => {
        localStorage.removeItem('romatec_token');
        localStorage.removeItem('romatec_user');
        setUser(null);
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await authAPI.login({ email, password });
    localStorage.setItem('romatec_token', res.token);
    localStorage.setItem('romatec_user', JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  };

  const register = async (data) => {
    const res = await authAPI.register(data);
    localStorage.setItem('romatec_token', res.token);
    localStorage.setItem('romatec_user', JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    localStorage.removeItem('romatec_token');
    localStorage.removeItem('romatec_user');
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const u = await authAPI.me();
      setUser(u);
      localStorage.setItem('romatec_user', JSON.stringify(u));
    } catch { /* noop */ }
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
};
