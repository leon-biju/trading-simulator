import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { AxiosError } from 'axios'
import ReactApexChart from 'react-apexcharts'
import type { ApexOptions } from 'apexcharts'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { getAsset, getChartData } from '@/api/market'
import { placeOrder, cancelOrder } from '@/api/trading'
import { useAuth } from '@/auth/AuthContext'
import { formatCurrency, formatDate } from '@/lib/utils'

const RANGES = ['1H', '1D', '1M', '6M', '1Y'] as const
type Range = typeof RANGES[number]

interface OrderForm {
  quantity: string
  limit_price: string
}

export default function AssetDetailPage() {
  const { exchangeCode, ticker } = useParams<{ exchangeCode: string; ticker: string }>()
  const [range, setRange] = useState<Range>('1D')
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY')
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET')
  const [orderError, setOrderError] = useState<string | null>(null)
  const [orderSuccess, setOrderSuccess] = useState(false)
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'
  const qc = useQueryClient()

  const { data: asset, isLoading: assetLoading } = useQuery({
    queryKey: ['asset', exchangeCode, ticker],
    queryFn: () => getAsset(exchangeCode!, ticker!),
    staleTime: 30_000,
    enabled: !!(exchangeCode && ticker),
  })

  const { data: chartData } = useQuery({
    queryKey: ['chart', exchangeCode, ticker, range],
    queryFn: () => getChartData(exchangeCode!, ticker!, range),
    staleTime: 60_000,
    enabled: !!(exchangeCode && ticker),
  })

  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<OrderForm>()
  const quantity  = watch('quantity')
  const limitPrice = watch('limit_price')

  const estimatedCost = (() => {
    const q = parseFloat(quantity)
    const priceStr = orderType === 'LIMIT' ? limitPrice : asset?.current_price ?? null
    const p = priceStr ? parseFloat(priceStr) : NaN
    if (isNaN(q) || isNaN(p) || q <= 0 || p <= 0) return null
    return (q * p).toFixed(2)
  })()

  const orderMutation = useMutation({
    mutationFn: placeOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['asset', exchangeCode, ticker] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['portfolio'] })
      qc.invalidateQueries({ queryKey: ['wallet'] })
      reset()
      setOrderError(null)
      setOrderSuccess(true)
      setTimeout(() => setOrderSuccess(false), 3000)
    },
    onError: (err: AxiosError<{ error?: string }>) => {
      setOrderError(err.response?.data?.error ?? 'Order failed.')
    },
  })

  const cancelMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['asset', exchangeCode, ticker] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['wallet'] })
    },
  })

  const onSubmit = (formData: OrderForm) => {
    setOrderError(null)
    setOrderSuccess(false)
    orderMutation.mutate({
      exchange_code: exchangeCode!,
      asset_symbol: ticker!,
      side,
      order_type: orderType,
      quantity: formData.quantity,
      limit_price: orderType === 'LIMIT' ? formData.limit_price : null,
    })
  }

  const chartSeries = (() => {
    if (!chartData) return []
    if (chartData.chart_type === 'candlestick' && chartData.candlestick_data) {
      return [{
        name: ticker ?? '',
        data: chartData.candlestick_data.map(d => ({ x: new Date(d.x * 1000), y: [d.o, d.h, d.l, d.c] })),
      }]
    }
    if (chartData.line_series) {
      return [{
        name: ticker ?? '',
        data: chartData.line_series.map(d => ({ x: new Date(d.x), y: d.y })),
      }]
    }
    return []
  })()

  const chartOptions: ApexOptions = {
    chart: {
      type: chartData?.chart_type === 'candlestick' ? 'candlestick' : 'line',
      background: 'transparent',
      toolbar: { show: false },
      animations: { enabled: false },
      fontFamily: 'IBM Plex Sans',
    },
    theme: { mode: 'dark' },
    grid: { borderColor: '#1E2840', strokeDashArray: 0 },
    xaxis: {
      type: 'datetime',
      labels: { style: { colors: '#475569', fontSize: '11px' } },
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      labels: {
        style: { colors: '#475569', fontSize: '11px' },
        formatter: (v) => formatCurrency(v, chartData?.currency_code ?? asset?.currency_code ?? 'USD', 2),
      },
    },
    plotOptions: {
      candlestick: { colors: { upward: '#10B981', downward: '#EF4444' } },
    },
    stroke: { curve: 'straight', width: 1.5, colors: ['#06B6D4'] },
    tooltip: {
      theme: 'dark',
      style: { fontFamily: 'IBM Plex Sans' },
    },
  }

  const inputCls = 'w-full rounded border border-edge bg-raised px-3 py-2 text-sm text-bright placeholder-faint focus:border-accent focus:outline-none transition-colors'

  return (
    <PageWrapper>
      {assetLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-accent" />
        </div>
      ) : asset ? (
        <div>
          {/* ── Breadcrumb ──────────────────────────────────────── */}
          <div className="mb-4 flex items-center gap-2 text-[11px] text-faint">
            <Link to="/market" className="hover:text-dim transition-colors">Markets</Link>
            <span>/</span>
            <Link to={`/market/${asset.exchange_code}`} className="hover:text-dim transition-colors">
              {asset.exchange_name}
            </Link>
            <span>/</span>
            <span className="text-dim">{asset.ticker}</span>
          </div>

          {/* ── Header ─────────────────────────────────────────── */}
          <div className="mb-5 flex flex-wrap items-baseline gap-3">
            <h1 className="text-xl font-semibold text-bright">{asset.name}</h1>
            <span className="text-sm text-faint">{asset.ticker}</span>
            <StatusBadge value={asset.is_exchange_open ? 'OPEN' : 'CLOSED'} />
            {asset.current_price && (
              <span className="ml-auto text-2xl font-semibold tabular-nums text-bright">
                {formatCurrency(asset.current_price, asset.currency_code)}
              </span>
            )}
          </div>

          {/* ── Chart + Order form ─────────────────────────────── */}
          <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Chart */}
            <div className="rounded-lg border border-edge bg-panel p-4 lg:col-span-2">
              <div className="mb-3 flex gap-0.5">
                {RANGES.map(r => (
                  <button
                    key={r}
                    onClick={() => setRange(r)}
                    className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                      range === r
                        ? 'bg-accent/15 text-accent'
                        : 'text-faint hover:text-dim'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
              {chartSeries.length > 0 ? (
                <ReactApexChart
                  type={chartData?.chart_type === 'candlestick' ? 'candlestick' : 'line'}
                  series={chartSeries}
                  options={chartOptions}
                  height={320}
                />
              ) : (
                <div className="flex h-64 items-center justify-center text-xs text-faint">
                  No chart data available
                </div>
              )}
            </div>

            {/* Order ticket */}
            <div className="space-y-4">
              <div className="rounded-lg border border-edge bg-panel p-4">
                {!asset.is_exchange_open && (
                  <div className="mb-4 rounded border border-yellow-500/20 bg-yellow-500/8 px-3 py-2 text-xs text-yellow-400">
                    Exchange closed — limit orders will be queued
                  </div>
                )}

                {/* BUY / SELL */}
                <div className="mb-4 flex rounded-md border border-edge overflow-hidden">
                  <button
                    onClick={() => setSide('BUY')}
                    className={`flex-1 py-2 text-xs font-semibold tracking-wider transition ${
                      side === 'BUY'
                        ? 'bg-buy text-white'
                        : 'text-dim hover:bg-raised'
                    }`}
                  >
                    BUY
                  </button>
                  <button
                    onClick={() => setSide('SELL')}
                    className={`flex-1 py-2 text-xs font-semibold tracking-wider transition ${
                      side === 'SELL'
                        ? 'bg-sell text-white'
                        : 'text-dim hover:bg-raised'
                    }`}
                  >
                    SELL
                  </button>
                </div>

                {/* MARKET / LIMIT */}
                <div className="mb-4 flex gap-2">
                  {(['MARKET', 'LIMIT'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setOrderType(t)}
                      className={`flex-1 rounded py-1.5 text-xs font-medium transition border ${
                        orderType === t
                          ? 'border-accent text-accent'
                          : 'border-edge text-faint hover:border-dim hover:text-dim'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                  <div>
                    <label className="mb-1 block text-[11px] uppercase tracking-wider text-faint">Quantity</label>
                    <input
                      type="number" step="any" min="0.0001" placeholder="0"
                      {...register('quantity', {
                        required: 'Required',
                        min: { value: 0.0001, message: 'Must be positive' },
                      })}
                      className={inputCls}
                    />
                    {errors.quantity && <p className="mt-1 text-xs text-sell">{errors.quantity.message}</p>}
                  </div>

                  {orderType === 'LIMIT' && (
                    <div>
                      <label className="mb-1 block text-[11px] uppercase tracking-wider text-faint">
                        Limit price ({asset.currency_code})
                      </label>
                      <input
                        type="number" step="any" min="0.0001" placeholder="0.00"
                        {...register('limit_price', {
                          required: orderType === 'LIMIT' ? 'Required' : false,
                          min: { value: 0.0001, message: 'Must be positive' },
                        })}
                        className={inputCls}
                      />
                      {errors.limit_price && <p className="mt-1 text-xs text-sell">{errors.limit_price.message}</p>}
                    </div>
                  )}

                  {estimatedCost && (
                    <div className="rounded border border-edge/50 bg-raised px-3 py-2 text-[11px] text-dim">
                      Est. {side === 'BUY' ? 'cost' : 'proceeds'}:{' '}
                      <span className="text-bright tabular-nums">{formatCurrency(estimatedCost, asset.currency_code)}</span>
                      <span className="ml-1 text-faint">(excl. fees)</span>
                    </div>
                  )}

                  {asset.user_wallet && (
                    <p className="text-[11px] text-faint">
                      Available:{' '}
                      <span className="text-dim tabular-nums">
                        {formatCurrency(asset.user_wallet.available_balance, asset.user_wallet.currency_code)}
                      </span>
                    </p>
                  )}

                  {orderError && <p className="text-xs text-sell">{orderError}</p>}
                  {orderSuccess && <p className="text-xs text-buy">Order placed</p>}

                  <button
                    type="submit"
                    disabled={orderMutation.isPending}
                    className={`w-full rounded py-2.5 text-sm font-semibold text-white transition disabled:opacity-50 ${
                      side === 'BUY'
                        ? 'bg-buy hover:bg-buy/90'
                        : 'bg-sell hover:bg-sell/90'
                    }`}
                  >
                    {orderMutation.isPending ? 'Placing…' : `${side} ${ticker}`}
                  </button>
                </form>
              </div>

              {/* Position */}
              {asset.user_position.has_position && (
                <div className="rounded-lg border border-edge bg-panel p-4">
                  <h2 className="mb-3 text-[11px] uppercase tracking-wider text-faint">Your position</h2>
                  <dl className="space-y-1.5">
                    {[
                      ['Quantity',  asset.user_position.quantity],
                      ['Available', asset.user_position.available_quantity],
                      asset.user_position.pending_quantity && parseFloat(asset.user_position.pending_quantity) > 0
                        ? ['Pending', asset.user_position.pending_quantity]
                        : null,
                      asset.user_position.average_cost
                        ? ['Avg cost', formatCurrency(asset.user_position.average_cost, asset.currency_code)]
                        : null,
                    ].filter(Boolean).map((item) => {
                      const [k, v] = item as [string, string]
                      return (
                        <div key={k} className="flex justify-between text-xs">
                          <dt className="text-faint">{k}</dt>
                          <dd className="tabular-nums text-dim">{v}</dd>
                        </div>
                      )
                    })}
                  </dl>
                </div>
              )}

              {/* Wallet */}
              {asset.user_wallet && (
                <div className="rounded-lg border border-edge bg-panel p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <h2 className="text-[11px] uppercase tracking-wider text-faint">
                      {asset.user_wallet.currency_code} wallet
                    </h2>
                    <Link to={`/wallets/${asset.user_wallet.currency_code}`} className="text-[11px] text-accent hover:text-accent/80">
                      View →
                    </Link>
                  </div>
                  <dl className="space-y-1">
                    {[
                      ['Balance',   formatCurrency(asset.user_wallet.balance,           asset.user_wallet.currency_code)],
                      ['Available', formatCurrency(asset.user_wallet.available_balance,  asset.user_wallet.currency_code)],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between text-xs">
                        <dt className="text-faint">{k}</dt>
                        <dd className="tabular-nums text-dim">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}
            </div>
          </div>

          {/* ── Pending orders for this asset ─────────────────── */}
          {asset.pending_orders.length > 0 && (
            <div className="rounded-lg border border-edge bg-panel">
              <div className="border-b border-edge px-4 py-3">
                <h2 className="text-[11px] uppercase tracking-wider text-faint">Your pending orders</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-edge/60 text-[11px] uppercase tracking-wider text-faint">
                      <th className="px-4 py-2.5 text-left font-medium">Date</th>
                      <th className="px-4 py-2.5 text-left font-medium">Side</th>
                      <th className="px-4 py-2.5 text-left font-medium">Type</th>
                      <th className="px-4 py-2.5 text-right font-medium">Qty</th>
                      <th className="px-4 py-2.5 text-right font-medium">Limit</th>
                      <th className="px-4 py-2.5 text-left font-medium">Status</th>
                      <th className="px-4 py-2.5"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {asset.pending_orders.map((o) => (
                      <tr key={o.id} className="border-b border-edge/40 last:border-0 hover:bg-raised/40 transition-colors">
                        <td className="px-4 py-2.5 text-[11px] text-faint">{formatDate(o.created_at)}</td>
                        <td className="px-4 py-2.5"><StatusBadge value={o.side} /></td>
                        <td className="px-4 py-2.5 text-xs text-faint">{o.order_type}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">{o.quantity}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-faint">
                          {o.limit_price ? formatCurrency(o.limit_price, asset.currency_code) : '—'}
                        </td>
                        <td className="px-4 py-2.5"><StatusBadge value={o.status} /></td>
                        <td className="px-4 py-2.5 text-right">
                          {o.status === 'PENDING' && (
                            <button
                              onClick={() => cancelMutation.mutate(o.id)}
                              disabled={cancelMutation.isPending}
                              className="text-[11px] text-sell hover:text-sell/80 disabled:opacity-40"
                            >
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Exchange footer */}
          <p className="mt-4 text-[11px] text-faint">
            {asset.exchange_name} · {asset.exchange_timezone} · {asset.exchange_open_time}–{asset.exchange_close_time}
            {user && <span className="ml-2">· Home: {homeCurrency}</span>}
          </p>
        </div>
      ) : (
        <p className="text-dim">Asset not found.</p>
      )}
    </PageWrapper>
  )
}
