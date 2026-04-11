import { cn, pnlClass, formatCurrency, formatPercent } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

interface Props {
  value: string | number | null | undefined
  currency?: string
  percent?: number | null
  size?: 'sm' | 'md'
}

const BG_MAP: Record<string, string> = {
  'text-buy':  'bg-buy/10 border-buy/20',
  'text-sell': 'bg-sell/10 border-sell/20',
  'text-dim':  'bg-raised border-edge',
}

export default function PnlBadge({ value, currency, percent, size = 'md' }: Props) {
  const cls = pnlClass(value)
  const bg  = BG_MAP[cls] ?? 'bg-raised border-edge'

  return (
    <Badge
      className={cn(
        cls, bg,
        'tabular-nums font-medium border',
        size === 'sm' ? 'text-xs px-1.5 py-0' : 'text-sm px-2 py-0.5',
      )}
    >
      {currency ? formatCurrency(value, currency) : (value ?? '—')}
      {percent != null && (
        <span className="ml-1.5 opacity-60">{formatPercent(percent)}</span>
      )}
    </Badge>
  )
}
