import React, { createContext, useContext, useState, useCallback } from "react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface NotificationContextType {
  toasts: Toast[];
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const add = useCallback((type: ToastType, message: string) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  }, []);

  return (
    <NotificationContext.Provider
      value={{
        toasts,
        success: (m) => add("success", m),
        error: (m) => add("error", m),
        info: (m) => add("info", m),
        warning: (m) => add("warning", m),
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotification(): NotificationContextType {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotification must be used within NotificationProvider");
  return ctx;
}
