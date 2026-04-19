import React from "react";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export function Textarea({ label, error, className = "", id, ...props }: TextareaProps) {
  const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={textareaId} className="block text-sm font-medium text-gray-300">
          {label}
        </label>
      )}
      <textarea
        id={textareaId}
        className={`w-full bg-gray-800 border rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm resize-none
          focus:outline-none focus:ring-1 transition-colors
          ${error
            ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/30"
            : "border-gray-700 focus:border-green-600 focus:ring-green-600/30"
          } ${className}`}
        {...props}
      />
      {error && <p className="text-red-400 text-xs">{error}</p>}
    </div>
  );
}
