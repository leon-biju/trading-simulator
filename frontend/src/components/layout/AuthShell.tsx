import type { ReactNode } from 'react'

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[calc(100svh-3rem)] lg:min-h-svh items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        {children}
      </div>
    </div>
  )
}
