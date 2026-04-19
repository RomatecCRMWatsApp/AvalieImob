import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({ label, error, hint, className = "", id, ...props }: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-gray-300">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`w-full bg-gray-800 border rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm
          focus:outline-none focus:ring-1 transition-colors
          ${error
            ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/30"
            : "border-gray-700 focus:border-green-600 focus:ring-green-600/30"
          } ${className}`}
        {...props}
      />
      {hint && !error && <p className="text-gray-500 text-xs">{hint}</p>}
      {error && <p className="text-red-400 text-xs">{error}</p>}
    </div>
  );
}
