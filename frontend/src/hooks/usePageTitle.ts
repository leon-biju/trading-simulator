import { useEffect } from 'react'

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = `${title} - Trading Simulator`
    return () => {
      document.title = 'Trading Simulator'
    }
  }, [title])
}
