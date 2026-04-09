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
  const quantity = watch('quantity')
  const limitPrice = watch('limit_price')

  // Rough cost estimate (display-only, never used for actual calculation)
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

  // Build ApexCharts series
  const chartSeries = (() => {
    if (!chartData) return []
    if (chartData.chart_type === 'candlestick' && chartData.candlestick_data) {
      return [{
        name: ticker ?? '',
        data: chartData.candlestick_data.map(d => ({
          x: new Date(d.x * 1000),
          y: [d.o, d.h, d.l, d.c],
        })),
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
    },
    theme: { mode: 'dark' },
    grid: { borderColor: '#1e293b' },
    xaxis: { type: 'datetime', labels: { style: { colors: '#64748b' } } },
    yaxis: {
      labels: {
        style: { colors: '#64748b' },
        formatter: (v) => formatCurrency(v, chartData?.currency_code ?? asset?.currency_code ?? 'USD', 2),
      },
    },
    plotOptions: {
      candlestick: {
        colors: { upward: '#34d399', downward: '#f87171' },
      },
    },
    stroke: { curve: 'smooth', width: 2, colors: ['#6366f1'] },
    tooltip: { theme: 'dark' },
  }

  return (
    <PageWrapper>
      {assetLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
        </div>
      ) : asset ? (
        <div className="space-y-6">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Link to="/market" className="hover:text-slate-300">Markets</Link>
            <span>/</span>
            <Link to={`/market/${asset.exchange_code}`} className="hover:text-slate-300">
              {asset.exchange_name}
            </Link>
            <span>/</span>
            <span className="text-slate-300">{asset.ticker}</span>
          </div>

          {/* Header */}
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold text-white">{asset.name}</h1>
            <span className="text-sm text-slate-500">{asset.ticker}</span>
            <StatusBadge value={asset.is_exchange_open ? 'OPEN' : 'CLOSED'} />
            {asset.current_price && (
              <span className="ml-auto text-xl font-semibold text-white">
                {formatCurrency(asset.current_price, asset.currency_code)}
              </span>
            )}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Chart */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 lg:col-span-2">
              {/* Range selector */}
              <div className="mb-3 flex gap-1">
                {RANGES.map(r => (
                  <button
                    key={r}
                    onClick={() => setRange(r)}
                    className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                      range === r
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-500 hover:text-slate-300'
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
                  height={300}
                />
              ) : (
                <div className="flex h-64 items-center justify-center text-sm text-slate-500">
                  No chart data available.
                </div>
              )}
            </div>

            {/* Right sidebar */}
            <div className="space-y-4">
              {/* Place order form */}
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <h2 className="mb-3 text-sm font-medium text-slate-300">Place order</h2>

                {!asset.is_exchange_open && (
                  <div className="mb-3 rounded-lg bg-amber-900/30 px-3 py-2 text-xs text-amber-400">
                    Exchange is closed. Limit orders will be queued.
                  </div>
                )}

                {/* BUY / SELL toggle */}
                <div className="mb-3 flex rounded-lg border border-slate-700 p-0.5">
                  <button
                    onClick={() => setSide('BUY')}
                    className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition ${
                      side === 'BUY' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    BUY
                  </button>
                  <button
                    onClick={() => setSide('SELL')}
                    className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition ${
                      side === 'SELL' ? 'bg-red-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    SELL
                  </button>
                </div>

                {/* MARKET / LIMIT toggle */}
                <div className="mb-3 flex gap-2">
                  {(['MARKET', 'LIMIT'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setOrderType(t)}
                      className={`flex-1 rounded-lg border py-1.5 text-xs font-medium transition ${
                        orderType === t
                          ? 'border-indigo-500 text-indigo-400'
                          : 'border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">Quantity</label>
                    <input
                      type="number"
                      step="any"
                      min="0.0001"
                      placeholder="0"
                      {...register('quantity', {
                        required: 'Quantity is required',
                        min: { value: 0.0001, message: 'Must be positive' },
                      })}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                    />
                    {errors.quantity && (
                      <p className="mt-1 text-xs text-red-400">{errors.quantity.message}</p>
                    )}
                  </div>

                  {orderType === 'LIMIT' && (
                    <div>
                      <label className="mb-1 block text-xs text-slate-500">
                        Limit price ({asset.currency_code})
                      </label>
                      <input
                        type="number"
                        step="any"
                        min="0.0001"
                        placeholder="0.00"
                        {...register('limit_price', {
                          required: orderType === 'LIMIT' ? 'Limit price is required' : false,
                          min: { value: 0.0001, message: 'Must be positive' },
                        })}
                        className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                      />
                      {errors.limit_price && (
                        <p className="mt-1 text-xs text-red-400">{errors.limit_price.message}</p>
                      )}
                    </div>
                  )}

                  {/* Cost estimate */}
                  {estimatedCost && (
                    <div className="rounded-lg bg-slate-800/50 px-3 py-2 text-xs text-slate-400">
                      Est. {side === 'BUY' ? 'cost' : 'proceeds'}:{' '}
                      {formatCurrency(estimatedCost, asset.currency_code)}
                      <span className="ml-1 text-slate-600">(excl. fees)</span>
                    </div>
                  )}

                  {/* Wallet balance for context */}
                  {asset.user_wallet && (
                    <p className="text-xs text-slate-500">
                      Available:{' '}
                      <span className="text-slate-300">
                        {formatCurrency(asset.user_wallet.available_balance, asset.user_wallet.currency_code)}
                      </span>
                    </p>
                  )}

                  {orderError && <p className="text-xs text-red-400">{orderError}</p>}
                  {orderSuccess && <p className="text-xs text-emerald-400">Order placed successfully!</p>}

                  <button
                    type="submit"
                    disabled={orderMutation.isPending}
                    className={`w-full rounded-lg py-2 text-sm font-semibold text-white transition disabled:opacity-50 ${
                      side === 'BUY'
                        ? 'bg-emerald-600 hover:bg-emerald-500'
                        : 'bg-red-600 hover:bg-red-500'
                    }`}
                  >
                    {orderMutation.isPending ? 'Placing…' : `${side} ${ticker}`}
                  </button>
                </form>
              </div>

              {/* Position */}
              {asset.user_position.has_position && (
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <h2 className="mb-3 text-sm font-medium text-slate-300">Your position</h2>
                  <dl className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Quantity</dt>
                      <dd className="tabular-nums text-slate-300">{asset.user_position.quantity}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Available</dt>
                      <dd className="tabular-nums text-slate-300">{asset.user_position.available_quantity}</dd>
                    </div>
                    {asset.user_position.pending_quantity && parseFloat(asset.user_position.pending_quantity) > 0 && (
                      <div className="flex justify-between">
                        <dt className="text-slate-500">Pending</dt>
                        <dd className="tabular-nums text-slate-400">{asset.user_position.pending_quantity}</dd>
                      </div>
                    )}
                    {asset.user_position.average_cost && (
                      <div className="flex justify-between">
                        <dt className="text-slate-500">Avg cost</dt>
                        <dd className="tabular-nums text-slate-300">
                          {formatCurrency(asset.user_position.average_cost, asset.currency_code)}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>
              )}

              {/* Wallet info */}
              {asset.user_wallet && (
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-medium text-slate-300">
                      {asset.user_wallet.currency_code} wallet
                    </h2>
                    <Link
                      to={`/wallets/${asset.user_wallet.currency_code}`}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      View →
                    </Link>
                  </div>
                  <dl className="mt-2 space-y-1 text-xs">
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Balance</dt>
                      <dd className="tabular-nums text-slate-300">
                        {formatCurrency(asset.user_wallet.balance, asset.user_wallet.currency_code)}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Available</dt>
                      <dd className="tabular-nums text-slate-300">
                        {formatCurrency(asset.user_wallet.available_balance, asset.user_wallet.currency_code)}
                      </dd>
                    </div>
                  </dl>
                </div>
              )}
            </div>
          </div>

          {/* Pending orders for this asset */}
          {asset.pending_orders.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900">
              <div className="border-b border-slate-800 px-4 py-3">
                <h2 className="text-sm font-medium text-slate-300">Your pending orders</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs text-slate-500">
                      <th className="px-4 py-3 text-left">Date</th>
                      <th className="px-4 py-3 text-left">Side</th>
                      <th className="px-4 py-3 text-left">Type</th>
                      <th className="px-4 py-3 text-right">Qty</th>
                      <th className="px-4 py-3 text-right">Limit price</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {asset.pending_orders.map((o) => (
                      <tr key={o.id} className="border-b border-slate-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-xs text-slate-400">{formatDate(o.created_at)}</td>
                        <td className="px-4 py-2.5"><StatusBadge value={o.side} /></td>
                        <td className="px-4 py-2.5 text-xs text-slate-400">{o.order_type}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">{o.quantity}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-slate-400">
                          {o.limit_price ? formatCurrency(o.limit_price, asset.currency_code) : '—'}
                        </td>
                        <td className="px-4 py-2.5"><StatusBadge value={o.status} /></td>
                        <td className="px-4 py-2.5 text-right">
                          {o.status === 'PENDING' && (
                            <button
                              onClick={() => cancelMutation.mutate(o.id)}
                              disabled={cancelMutation.isPending}
                              className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
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

          {/* Exchange info footer */}
          <div className="text-xs text-slate-600">
            {asset.exchange_name} · {asset.exchange_timezone} ·{' '}
            {asset.exchange_open_time}–{asset.exchange_close_time}{' '}
            {user && (
              <span className="ml-1 text-slate-700">· Home currency: {homeCurrency}</span>
            )}
          </div>
        </div>
      ) : (
        <p className="text-slate-400">Asset not found.</p>
      )}
    </PageWrapper>
  )
}
