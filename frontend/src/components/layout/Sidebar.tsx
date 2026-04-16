import { Link, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, TrendingUp, LogOut, ChevronsUpDown, LogIn, UserPlus, UserRound, Settings } from 'lucide-react'
import { useAuth } from '@/auth/AuthContext'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupContent,
} from '@/components/ui/sidebar'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const ANON_NAV = [
  { to: '/market', label: 'Markets', icon: TrendingUp },
]

const APP_NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/market',    label: 'Markets',   icon: TrendingUp },
]

export default function AppSidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const initials = user?.username?.[0]?.toUpperCase() ?? '?'
  const nav = user ? APP_NAV : ANON_NAV

  return (
    <Sidebar collapsible="icon">
      {/* ── Header / Logo ─────────────────────────────── */}
      <SidebarHeader className="px-3 py-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild className="hover:bg-transparent active:bg-transparent">
              <Link to={user ? '/dashboard' : '/market'} className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand text-sm font-bold text-base leading-none select-none">
                  TS
                </div>
                <span className="text-sm font-semibold tracking-tight text-bright">
                  Trading<span className="text-brand"> Simulator</span>
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* ── Nav ───────────────────────────────────────── */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {nav.map(({ to, label, icon: Icon }) => (
                <SidebarMenuItem key={to}>
                  <NavLink to={to}>
                    {({ isActive }) => (
                      <SidebarMenuButton isActive={isActive} tooltip={label} className="gap-3">
                        <Icon className="size-4 shrink-0" />
                        <span>{label}</span>
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* ── Footer ────────────────────────────────────── */}
      <SidebarFooter className="px-3 py-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                {user ? (
                  <SidebarMenuButton
                    size="lg"
                    className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                    tooltip={user.username ?? 'Account'}
                  >
                    <Avatar className="h-7 w-7 shrink-0">
                      <AvatarFallback className="bg-raised border border-edge text-dim text-xs font-medium">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0 text-left leading-none">
                      <p className="truncate text-xs font-medium text-bright">{user.username}</p>
                      <p className="text-[11px] text-faint mt-0.5">{user.home_currency}</p>
                    </div>
                    <ChevronsUpDown className="size-3.5 shrink-0 text-faint" />
                  </SidebarMenuButton>
                ) : (
                  <SidebarMenuButton
                    size="lg"
                    className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                    tooltip="Sign in"
                  >
                    <Avatar className="h-7 w-7 shrink-0">
                      <AvatarFallback className="bg-raised border border-edge text-dim text-xs font-medium">
                        <UserRound className="size-3.5" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0 text-left leading-none">
                      <p className="text-xs font-medium text-bright">Sign in</p>
                      <p className="text-[11px] text-faint mt-0.5">or create account</p>
                    </div>
                    <ChevronsUpDown className="size-3.5 shrink-0 text-faint" />
                  </SidebarMenuButton>
                )}
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-52 mb-1">
                {user ? (
                  <>
                    <DropdownMenuItem asChild className="gap-2">
                      <Link to="/settings">
                        <Settings className="size-4" />
                        Settings
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="text-sell focus:text-sell focus:bg-sell/10 gap-2"
                    >
                      <LogOut className="size-4" />
                      Sign out
                    </DropdownMenuItem>
                  </>
                ) : (
                  <>
                    <DropdownMenuItem asChild className="gap-2">
                      <Link to="/login">
                        <LogIn className="size-4" />
                        Sign in
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild className="gap-2">
                      <Link to="/register">
                        <UserPlus className="size-4" />
                        Create account
                      </Link>
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
