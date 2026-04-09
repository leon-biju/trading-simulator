import { pnlClass, formatCurrency, formatPercent } from '@/lib/utils'

interface Props {
  value: string | number | null | undefined
  currency?: string
  percent?: number | null
  size?: 'sm' | 'md'
}

export default function PnlBadge({ value, currency, percent, size = 'md' }: Props) {
  const cls = pnlClass(value)
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm'

  return (
    <span className={`${cls} ${textSize} font-medium tabular-nums`}>
      {currency ? formatCurrency(value, currency) : value ?? '—'}
      {percent != null && (
        <span className="ml-1.5 opacity-75">{formatPercent(percent)}</span>
      )}
    </span>
  )
}
