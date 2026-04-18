import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

const STATUS_STYLES: Record<string, string> = {
  FILLED:    'bg-buy/10 text-buy border-buy/20',
  PENDING:   'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  CANCELLED: 'bg-raised text-faint border-edge',
  REJECTED:  'bg-sell/10 text-sell border-sell/20',
  EXPIRED:   'bg-raised text-faint border-edge',
  BUY:       'bg-buy/10 text-buy border-buy/20',
  SELL:      'bg-sell/10 text-sell border-sell/20',
  OPEN:      'bg-buy/10 text-buy border-buy/20',
  CLOSED:    'bg-raised text-dim border-edge',
}

export default function StatusBadge({ value }: { value: string }) {
  return (
    <Badge
      className={cn(
        'text-[11px] tracking-wide font-medium border',
        STATUS_STYLES[value] ?? 'bg-raised text-dim border-edge',
      )}
    >
      {value}
    </Badge>
  )
}
