import React from "react";
import { CheckCircle, XCircle, Info, AlertTriangle } from "lucide-react";
import { useNotification } from "../../contexts/NotificationContext";

export function ToastContainer() {
  const { toasts } = useNotification();
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium border animate-in slide-in-from-right
            ${toast.type === "success" ? "bg-gray-900 border-green-700/60 text-green-300" : ""}
            ${toast.type === "error" ? "bg-gray-900 border-red-700/60 text-red-300" : ""}
            ${toast.type === "info" ? "bg-gray-900 border-blue-700/60 text-blue-300" : ""}
            ${toast.type === "warning" ? "bg-gray-900 border-yellow-700/60 text-yellow-300" : ""}
          `}
        >
          {toast.type === "success" && <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />}
          {toast.type === "error" && <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
          {toast.type === "info" && <Info className="w-4 h-4 text-blue-400 flex-shrink-0" />}
          {toast.type === "warning" && <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0" />}
          <span>{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
