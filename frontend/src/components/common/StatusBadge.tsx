const STATUS_STYLES: Record<string, string> = {
  FILLED:    'bg-buy/10 text-buy',
  PENDING:   'bg-yellow-500/10 text-yellow-400',
  CANCELLED: 'bg-raised text-faint',
  REJECTED:  'bg-sell/10 text-sell',
  EXPIRED:   'bg-raised text-faint',
  BUY:       'bg-buy/10 text-buy',
  SELL:      'bg-sell/10 text-sell',
  OPEN:      'bg-buy/10 text-buy',
  CLOSED:    'bg-raised text-dim',
}

export default function StatusBadge({ value }: { value: string }) {
  const style = STATUS_STYLES[value] ?? 'bg-raised text-dim'
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium tracking-wide ${style}`}>
      {value}
    </span>
  )
}
