import api from '@/lib/axios'

export interface Order {
  id: number
  asset_ticker: string
  asset_name: string
  exchange_code: string
  side: 'BUY' | 'SELL'
  order_type: 'MARKET' | 'LIMIT'
  quantity: string
  limit_price: string | null
  reserved_amount: string
  status: string
  created_at: string
  updated_at: string
  cancelled_at: string | null
}

export interface Trade {
  id: number
  asset_ticker: string
  asset_name: string
  exchange_code: string
  asset_currency_code: string
  side: 'BUY' | 'SELL'
  quantity: string
  price: string
  fee: string
  fee_currency_code: string
  total_value: string
  net_amount: string
  price_home: string | null
  total_value_home: string | null
  fee_home: string | null
  net_amount_home: string | null
  executed_at: string
}

export interface Position {
  id: number
  asset_ticker: string
  asset_name: string
  exchange_code: string
  asset_currency_code: string
  quantity: string
  pending_quantity: string
  available_quantity: string
  average_cost: string
  realized_pnl: string
  cost_basis: string
  current_price: string | null
  current_value: string | null
  unrealized_pnl: string | null
  pnl_percent: number | null
  current_price_home: string | null
  current_value_home: string | null
  unrealized_pnl_home: string | null
  cost_basis_home: string | null
  avg_cost_home: string | null
  realized_pnl_home: string | null
}

export interface Portfolio {
  home_currency: string
  total_value: string
  total_cost: string
  total_pnl: string | null
  pnl_percent: number | null
  positions: Position[]
}

export interface PortfolioHistory {
  labels: string[]
  datasets: {
    total_assets: number[]
    portfolio_value: number[]
    cash_balance: number[]
  }
  currency: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PlaceOrderPayload {
  exchange_code: string
  asset_symbol: string
  side: 'BUY' | 'SELL'
  order_type: 'MARKET' | 'LIMIT'
  quantity: string
  limit_price?: string | null
}

export async function getPortfolio(): Promise<Portfolio> {
  const { data } = await api.get('/api/trading/portfolio/')
  return data
}

export async function getPortfolioHistory(range: string): Promise<PortfolioHistory> {
  const { data } = await api.get('/api/trading/portfolio/history/', { params: { range } })
  return data
}

export async function getOrders(page = 1): Promise<Paginated<Order>> {
  const { data } = await api.get('/api/trading/orders/', { params: { page } })
  return data
}

export async function placeOrder(payload: PlaceOrderPayload): Promise<Order> {
  const { data } = await api.post('/api/trading/orders/', payload)
  return data
}

export async function cancelOrder(orderId: number): Promise<Order> {
  const { data } = await api.post(`/api/trading/orders/${orderId}/cancel/`)
  return data
}

export async function getTrades(page = 1): Promise<Paginated<Trade>> {
  const { data } = await api.get('/api/trading/trades/', { params: { page } })
  return data
}

export async function getPosition(
  exchangeCode: string,
  ticker: string,
): Promise<Position & { has_position: boolean }> {
  const { data } = await api.get(`/api/trading/position/${exchangeCode}/${ticker}/`)
  return data
}
