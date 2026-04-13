import { QueryClient } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s default
      gcTime: 5 * 60_000,       // 5m garbage collection
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default queryClient
