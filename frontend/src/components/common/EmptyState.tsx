import type { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  title: string
  description?: string
}

export default function EmptyState({ icon: Icon, title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-6 text-center">
      <Icon className="size-8 text-faint opacity-60" strokeWidth={1.5} />
      <p className="text-sm text-dim">{title}</p>
      {description && (
        <p className="text-xs text-faint">{description}</p>
      )}
    </div>
  )
}
