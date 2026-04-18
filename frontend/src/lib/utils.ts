import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

// WARNING: Must match config/constants.py TRADING_FEE_PERCENTAGE
// If you edit this also edit the config/constants.py
export const TRADING_FEE_RATE = 0.001

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  GBP: '£',
  USD: '$',
  EUR: '€',
  JPY: '¥',
}

export function formatCurrency(
  amount: string | number | null | undefined,
  currencyCode: string,
  decimals = 2,
): string {
  if (amount == null) return '—'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '—'
  const symbol = CURRENCY_SYMBOLS[currencyCode] ?? currencyCode + ' '
  return `${symbol}${num.toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDateShort(isoString: string): string {
  return new Date(isoString).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function pnlClass(value: string | number | null | undefined): string {
  if (value == null) return 'text-dim'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return 'text-dim'
  if (num > 0) return 'text-buy'
  if (num < 0) return 'text-sell'
  return 'text-dim'
}
