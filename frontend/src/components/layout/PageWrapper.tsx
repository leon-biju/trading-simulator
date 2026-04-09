import Navbar from './Navbar'

interface Props {
  children: React.ReactNode
  title?: string
}

export default function PageWrapper({ children, title }: Props) {
  return (
    <div className="min-h-screen bg-[#0f1117]">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-6">
        {title && (
          <h1 className="mb-6 text-xl font-semibold text-white">{title}</h1>
        )}
        {children}
      </main>
    </div>
  )
}
