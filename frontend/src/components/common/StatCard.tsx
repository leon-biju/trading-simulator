import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Trend {
  direction: 'up' | 'down' | 'neutral'
  label: string
}

interface Props {
  label: string
  value: ReactNode
  subvalue?: string
  trend?: Trend
}

const TREND_STYLES = {
  up:      { cls: 'bg-buy/10 text-buy border-buy/20',   Icon: TrendingUp },
  down:    { cls: 'bg-sell/10 text-sell border-sell/20', Icon: TrendingDown },
  neutral: { cls: 'bg-raised text-dim border-edge',     Icon: Minus },
}

export default function StatCard({ label, value, subvalue, trend }: Props) {
  const trendConfig = trend ? TREND_STYLES[trend.direction] : null

  return (
    <Card className="bg-panel border-edge">
      <CardContent className="px-4 py-3">
        <CardDescription className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">
          {label}
        </CardDescription>
        <div className="text-xl font-semibold tabular-nums text-bright leading-none">
          {value}
        </div>
        {(trend || subvalue) && (
          <div className="mt-2 flex items-center gap-2">
            {trendConfig && trend && (
              <Badge className={cn('text-[11px] font-medium border gap-1', trendConfig.cls)}>
                <trendConfig.Icon className="size-3" />
                {trend.label}
              </Badge>
            )}
            {subvalue && (
              <span className="text-[11px] text-faint">{subvalue}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
