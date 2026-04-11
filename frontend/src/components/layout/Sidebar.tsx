import { Link, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, TrendingUp, Briefcase, LogOut, ChevronsUpDown } from 'lucide-react'
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

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/market',    label: 'Markets',   icon: TrendingUp },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
]

export default function AppSidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const initials = user?.username?.[0]?.toUpperCase() ?? '?'

  return (
    <Sidebar collapsible="icon">
      {/* ── Header / Logo ─────────────────────────────── */}
      <SidebarHeader className="px-3 py-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild className="hover:bg-transparent active:bg-transparent">
              <Link to="/dashboard" className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent text-sm font-bold text-base leading-none select-none">
                  TS
                </div>
                <span className="text-sm font-semibold tracking-tight text-bright">
                  Trade<span className="text-accent">Sim</span>
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
              {NAV.map(({ to, label, icon: Icon }) => (
                <SidebarMenuItem key={to}>
                  <NavLink to={to}>
                    {({ isActive }) => (
                      <SidebarMenuButton
                        isActive={isActive}
                        tooltip={label}
                        className="gap-3"
                      >
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

      {/* ── Footer / User ─────────────────────────────── */}
      <SidebarFooter className="px-3 py-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                  tooltip={user?.username ?? 'Account'}
                >
                  <Avatar className="h-7 w-7 shrink-0">
                    <AvatarFallback className="bg-raised border border-edge text-dim text-xs font-medium">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0 text-left leading-none">
                    <p className="truncate text-xs font-medium text-bright">{user?.username}</p>
                    <p className="text-[11px] text-faint mt-0.5">{user?.home_currency}</p>
                  </div>
                  <ChevronsUpDown className="size-3.5 shrink-0 text-faint" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                side="top"
                align="start"
                className="w-52 mb-1"
              >
                <DropdownMenuItem
                  onClick={handleLogout}
                  className="text-sell focus:text-sell focus:bg-sell/10 gap-2"
                >
                  <LogOut className="size-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
