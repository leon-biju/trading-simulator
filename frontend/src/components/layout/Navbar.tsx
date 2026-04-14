import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm transition ${isActive ? 'text-white font-medium' : 'text-slate-400 hover:text-white'}`

  return (
    <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        {/* Brand */}
        <Link to="/dashboard" className="text-sm font-semibold text-white tracking-tight">
          Trading<span className="text-indigo-400">Sim</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-6 sm:flex">
          <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
          <NavLink to="/market" className={linkClass}>Markets</NavLink>
        </div>

        {/* User menu */}
        <div className="hidden items-center gap-3 sm:flex">
          <span className="text-xs text-slate-500">{user?.username}</span>
          <button
            onClick={handleLogout}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 transition hover:border-slate-500 hover:text-white"
          >
            Sign out
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="sm:hidden text-slate-400 hover:text-white"
          onClick={() => setMenuOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {menuOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            }
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="border-t border-slate-800 bg-slate-900 px-4 py-3 sm:hidden">
          <div className="flex flex-col gap-3">
            {[
              ['/dashboard', 'Dashboard'],
              ['/market', 'Markets'],
            ].map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                className={linkClass}
                onClick={() => setMenuOpen(false)}
              >
                {label}
              </NavLink>
            ))}
            <button
              onClick={handleLogout}
              className="text-left text-sm text-red-400 hover:text-red-300"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
