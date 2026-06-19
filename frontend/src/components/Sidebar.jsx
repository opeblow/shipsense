import { NavLink, useSearchParams } from 'react-router-dom';

const ITEMS = [
  { to: '/dashboard', label: 'Overview', icon: '01' },
  { to: '/dashboard/behavior', label: 'User Behavior', icon: '02' },
  { to: '/dashboard/insights', label: 'AI Insights', icon: '03' },
  { to: '/dashboard/ask', label: 'Ask Agent', icon: '04' },
  { to: '/dashboard/settings', label: 'Settings', icon: '05' },
];

function SidebarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="1" width="14" height="14" rx="2" />
      <line x1="5" y1="5" x2="11" y2="5" />
      <line x1="5" y1="8" x2="9" y2="8" />
      <line x1="5" y1="11" x2="7" y2="11" />
    </svg>
  );
}

export default function Sidebar() {
  const [searchParams] = useSearchParams();

  function linkTo(base) {
    const productId = searchParams.get('productId');
    if (!productId) return base;
    return `${base}?productId=${productId}`;
  }

  return (
    <aside className="w-56 min-h-screen bg-sidebar flex flex-col border-r border-[#1a1a1a]">
      <div className="px-5 py-6 border-b border-[#1a1a1a]">
        <NavLink to="/" className="text-sm font-semibold text-white tracking-tight">
          ShipSense
        </NavLink>
      </div>

      <nav className="flex-1 py-4">
        {ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={linkTo(item.to)}
            end={item.to === '/dashboard'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors duration-75
              ${isActive
                ? 'text-white font-semibold bg-sidebar-active border-l-2 border-accent'
                : 'text-[#9e9e9e] hover:text-white hover:bg-sidebar-hover border-l-2 border-transparent'
              }`
            }
          >
            <SidebarIcon n={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-[#1a1a1a]">
        <span className="text-xs text-[#6b6b6b]">ShipSense v0.1</span>
      </div>
    </aside>
  );
}
