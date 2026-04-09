import api from '@/lib/axios'

export interface Wallet {
  currency_code: string
  currency_name: string
  balance: string
  pending_balance: string
  available_balance: string
}

export interface Transaction {
  id: number
  amount: string
  balance_after: string
  source: string
  source_display: string
  timestamp: string
  description: string
}

export interface WalletDetail extends Wallet {
  transactions: {
    count: number
    next: string | null
    previous: string | null
    results: Transaction[]
  }
}

export interface FxTransferPayload {
  from_currency: string
  to_currency: string
  to_amount?: string
  from_amount?: string
}

export interface FxTransferResult {
  from_amount: string
  to_amount: string
  exchange_rate: string
  from_currency: string
  to_currency: string
}

export async function getWallets(): Promise<Wallet[]> {
  const { data } = await api.get('/api/wallets/')
  return data
}

export async function getWallet(currencyCode: string, page = 1): Promise<WalletDetail> {
  const { data } = await api.get(`/api/wallets/${currencyCode}/`, { params: { page } })
  return data
}

export async function fxTransfer(payload: FxTransferPayload): Promise<FxTransferResult> {
  const { data } = await api.post('/api/wallets/fx-transfer/', payload)
  return data
}
