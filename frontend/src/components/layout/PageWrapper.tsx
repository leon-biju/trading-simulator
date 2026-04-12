import { Link } from 'react-router-dom'
import AppSidebar from './Sidebar'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'

interface Props {
  children: React.ReactNode
}

export default function PageWrapper({ children }: Props) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {/* Mobile header */}
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-edge px-4 lg:hidden">
          <SidebarTrigger className="-ml-1 text-dim hover:text-bright" />
          <Separator orientation="vertical" className="h-4 bg-edge" />
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-brand text-xs font-bold text-base leading-none select-none">
              TS
            </div>
            <span className="text-sm font-semibold tracking-tight text-bright">
              Trade<span className="text-brand">Sim</span>
            </span>
          </Link>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 py-6 lg:px-6 lg:py-6">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
