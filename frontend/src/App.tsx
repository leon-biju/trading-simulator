import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/auth/AuthContext'
import { ProtectedRoute } from '@/auth/ProtectedRoute'

// Auth pages (small, not lazy-loaded — needed immediately)
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'

// App pages — lazy-loaded to keep initial bundle small
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const MarketOverviewPage = lazy(() => import('@/pages/MarketOverviewPage'))
const ExchangeDetailPage = lazy(() => import('@/pages/ExchangeDetailPage'))
const AssetDetailPage = lazy(() => import('@/pages/AssetDetailPage'))
const PortfolioPage = lazy(() => import('@/pages/PortfolioPage'))
const OrderHistoryPage = lazy(() => import('@/pages/OrderHistoryPage'))
const TradeHistoryPage = lazy(() => import('@/pages/TradeHistoryPage'))
const WalletDetailPage = lazy(() => import('@/pages/WalletDetailPage'))

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected */}
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/market" element={<MarketOverviewPage />} />
              <Route path="/market/:exchangeCode" element={<ExchangeDetailPage />} />
              <Route path="/market/:exchangeCode/:ticker" element={<AssetDetailPage />} />
              <Route path="/portfolio" element={<PortfolioPage />} />
              <Route path="/orders" element={<OrderHistoryPage />} />
              <Route path="/trades" element={<TradeHistoryPage />} />
              <Route path="/wallets/:currencyCode" element={<WalletDetailPage />} />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  )
}
