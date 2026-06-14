import { useState } from 'react';

export default function Input({ label, value, onChange, placeholder, type = 'text', error, hint, ...props }) {
  const [focused, setFocused] = useState(false);

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-text mb-1.5">{label}</label>
      )}
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className={`w-full py-2.5 text-sm bg-transparent border-b outline-none transition-colors duration-100
            ${focused ? 'border-accent' : 'border-border'}
            ${error ? 'border-error' : ''}
            placeholder:text-text-tertiary text-text`}
          {...props}
        />
      </div>
      {error && <p className="mt-1 text-xs text-error">{error}</p>}
      {hint && !error && <p className="mt-1 text-xs text-text-tertiary">{hint}</p>}
    </div>
  );
}
