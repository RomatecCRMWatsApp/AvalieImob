import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  children,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-green-500/40";

  const variants: Record<string, string> = {
    primary: "bg-green-700 hover:bg-green-600 text-white shadow-lg shadow-green-900/30",
    secondary: "bg-gray-700 hover:bg-gray-600 text-white",
    danger: "bg-red-700 hover:bg-red-600 text-white",
    ghost: "hover:bg-gray-800 text-gray-300 hover:text-white",
    outline: "border border-green-700 text-green-400 hover:bg-green-700/10",
  };

  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin flex-shrink-0" />
      )}
      {children}
    </button>
  );
}
