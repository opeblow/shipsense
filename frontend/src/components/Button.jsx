export default function Button({ children, variant = 'primary', onClick, type = 'button', disabled, className = '', ...props }) {
  const base = 'inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium transition-colors duration-100 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed';
  const variants = {
    primary: 'bg-accent text-white hover:bg-accent-hover active:bg-accent-hover',
    secondary: 'bg-transparent text-text border border-border hover:bg-zebra active:bg-border',
    ghost: 'bg-transparent text-text-secondary hover:text-text hover:bg-zebra',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
