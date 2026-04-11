import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

/* ── Icons ───────────────────────────────────────────────────── */
function IconDashboard() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.25" />
      <rect x="9"   y="1.5" width="5.5" height="5.5" rx="1.25" />
      <rect x="1.5" y="9"   width="5.5" height="5.5" rx="1.25" />
      <rect x="9"   y="9"   width="5.5" height="5.5" rx="1.25" />
    </svg>
  )
}

function IconMarkets() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <polyline points="1,12 4.5,7.5 7.5,9.5 11,5 15,3" strokeLinejoin="round" strokeLinecap="round" />
      <line x1="1" y1="14.5" x2="15" y2="14.5" strokeLinecap="round" />
    </svg>
  )
}

function IconPortfolio() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1.5" y="6" width="13" height="9" rx="1.5" />
      <path d="M5.5 6V4.5a2.5 2.5 0 015 0V6" strokeLinecap="round" />
    </svg>
  )
}

function IconUser() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="5.5" r="2.5" />
      <path d="M2 14.5c0-3.314 2.686-6 6-6s6 2.686 6 6" strokeLinecap="round" />
    </svg>
  )
}

function IconSignOut() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M10.5 10.5L13.5 8l-3-2.5" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="13.5" y1="8" x2="6" y2="8" strokeLinecap="round" />
      <path d="M6 13H3a1 1 0 01-1-1V4a1 1 0 011-1h3" strokeLinecap="round" />
    </svg>
  )
}

/* ── Nav items ───────────────────────────────────────────────── */
const NAV = [
  { to: '/dashboard', label: 'Dashboard', Icon: IconDashboard },
  { to: '/market',    label: 'Markets',   Icon: IconMarkets },
  { to: '/portfolio', label: 'Portfolio', Icon: IconPortfolio },
]

/* ── Inner content (shared between desktop + mobile overlay) ─── */
function SidebarInner({ onNav }: { onNav?: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    [
      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all select-none',
      isActive
        ? 'bg-accent/10 text-accent font-medium'
        : 'text-dim hover:bg-raised hover:text-bright',
    ].join(' ')

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <Link
        to="/dashboard"
        className="mb-8 flex items-center gap-2.5 px-3"
        onClick={onNav}
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-sm font-bold text-base leading-none">
          T
        </div>
        <span className="text-sm font-semibold tracking-tight text-bright">
          Trade<span className="text-accent">Sim</span>
        </span>
      </Link>

      {/* Nav links */}
      <nav className="flex flex-col gap-0.5">
        {NAV.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} className={linkCls} onClick={onNav}>
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User area */}
      <div className="mt-auto border-t border-edge pt-4">
        <div className="flex items-center gap-3 rounded-lg px-3 py-2">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-raised border border-edge text-dim">
            <IconUser />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-bright">{user?.username}</p>
            <p className="text-[11px] text-faint">{user?.home_currency}</p>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="text-faint transition hover:text-dim"
          >
            <IconSignOut />
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Main export ─────────────────────────────────────────────── */
export default function Sidebar() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Desktop — always visible */}
      <aside className="fixed inset-y-0 left-0 hidden w-56 border-r border-edge bg-panel px-3 py-6 lg:flex lg:flex-col">
        <SidebarInner />
      </aside>

      {/* Mobile top bar */}
      <header className="fixed inset-x-0 top-0 z-40 flex items-center justify-between border-b border-edge bg-panel/95 backdrop-blur px-4 h-12 lg:hidden">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-accent text-xs font-bold text-base leading-none">
            T
          </div>
          <span className="text-sm font-semibold text-bright">
            Trade<span className="text-accent">Sim</span>
          </span>
        </Link>
        <button
          onClick={() => setOpen(o => !o)}
          className="text-dim hover:text-bright transition p-1"
          aria-label="Toggle menu"
        >
          {open ? (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </header>

      {/* Mobile slide-over */}
      {open && (
        <div className="fixed inset-0 z-30 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-56 border-r border-edge bg-panel px-3 py-6 flex flex-col">
            <SidebarInner onNav={() => setOpen(false)} />
          </aside>
        </div>
      )}
    </>
  )
}
