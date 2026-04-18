import { useState, useEffect } from 'react'

const STORAGE_KEY = 'ts_recently_viewed'
const MAX_ITEMS = 10

export interface RecentAsset {
  exchangeCode: string
  ticker: string
  name: string
  price: string | null
  currency: string
  timestamp: number
}

function readStorage(): RecentAsset[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
  } catch {
    return []
  }
}

export function addRecentlyViewed(asset: Omit<RecentAsset, 'timestamp'>) {
  const existing = readStorage().filter(
    i => !(i.exchangeCode === asset.exchangeCode && i.ticker === asset.ticker),
  )
  const updated = [{ ...asset, timestamp: Date.now() }, ...existing].slice(0, MAX_ITEMS)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
}

export function useRecentlyViewed() {
  const [recent, setRecent] = useState<RecentAsset[]>(() => readStorage())

  useEffect(() => {
    setRecent(readStorage())
  }, [])

  return { recent }
}
