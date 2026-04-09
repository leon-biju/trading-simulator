import api from '@/lib/axios'

export interface Exchange {
  name: string
  code: string
  timezone: string
  open_time: string
  close_time: string
  is_open: boolean
  hours_until_open: number | null
  assets: Asset[]
  asset_count: number
}

export interface Asset {
  ticker: string
  name: string
  asset_type: string
  currency_code: string
  exchange_code: string
  is_active: boolean
  current_price: string | null
}

export interface AssetDetail {
  ticker: string
  name: string
  asset_type: string
  currency_code: string
  exchange_code: string
  exchange_name: string
  exchange_open_time: string
  exchange_close_time: string
  exchange_timezone: string
  is_exchange_open: boolean
  is_active: boolean
  current_price: string | null
  user_wallet: {
    balance: string
    available_balance: string
    pending_balance: string
    currency_code: string
  } | null
  user_position: {
    has_position: boolean
    quantity?: string
    available_quantity?: string
    average_cost?: string
    pending_quantity?: string
  }
  pending_orders: PendingOrder[]
}

export interface PendingOrder {
  id: number
  side: 'BUY' | 'SELL'
  order_type: 'MARKET' | 'LIMIT'
  quantity: string
  limit_price: string | null
  status: string
  created_at: string
}

export interface ChartData {
  chart_type: 'candlestick' | 'line'
  candlestick_data?: { x: number; o: number; h: number; l: number; c: number }[]
  line_series?: { x: string; y: number }[]
  currency_code: string
}

export interface FxRate {
  from_currency: string
  to_currency: string
  rate: string
  last_updated: string
}

export async function getExchanges(): Promise<Exchange[]> {
  const { data } = await api.get('/api/market/exchanges/')
  return data
}

export async function getExchange(code: string): Promise<Exchange> {
  const { data } = await api.get(`/api/market/exchanges/${code}/`)
  return data
}

export async function getAsset(exchangeCode: string, ticker: string): Promise<AssetDetail> {
  const { data } = await api.get(`/api/market/assets/${exchangeCode}/${ticker}/`)
  return data
}

export async function getChartData(
  exchangeCode: string,
  ticker: string,
  range: string,
): Promise<ChartData> {
  const { data } = await api.get(`/api/market/data/${exchangeCode}/${ticker}/`, {
    params: { range },
  })
  return data
}

export async function getFxRates(): Promise<FxRate[]> {
  const { data } = await api.get('/api/wallets/fx-rates/')
  return data
}
