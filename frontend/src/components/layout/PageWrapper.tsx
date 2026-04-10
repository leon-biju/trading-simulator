import Sidebar from './Sidebar'

interface Props {
  children: React.ReactNode
}

export default function PageWrapper({ children }: Props) {
  return (
    <div className="min-h-screen bg-base">
      <Sidebar />
      {/* Offset for sidebar on desktop, top bar on mobile */}
      <div className="lg:ml-56">
        <main className="mx-auto max-w-[1400px] px-4 py-6 pt-16 lg:px-8 lg:pt-8">
          {children}
        </main>
      </div>
    </div>
  )
}
