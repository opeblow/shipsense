export default function Card({ children, className = '', ...props }) {
  return (
    <div className={`bg-surface border border-border p-6 ${className}`} {...props}>
      {children}
    </div>
  );
}
