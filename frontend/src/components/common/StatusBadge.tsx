const STATUS_STYLES: Record<string, string> = {
  FILLED: 'bg-emerald-900/50 text-emerald-400',
  PENDING: 'bg-yellow-900/50 text-yellow-400',
  CANCELLED: 'bg-slate-800 text-slate-400',
  REJECTED: 'bg-red-900/50 text-red-400',
  EXPIRED: 'bg-slate-800 text-slate-500',
  BUY: 'bg-emerald-900/50 text-emerald-400',
  SELL: 'bg-red-900/50 text-red-400',
  OPEN: 'bg-emerald-900/50 text-emerald-400',
  CLOSED: 'bg-slate-800 text-slate-400',
}

export default function StatusBadge({ value }: { value: string }) {
  const style = STATUS_STYLES[value] ?? 'bg-slate-800 text-slate-400'
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${style}`}>
      {value}
    </span>
  )
}
