import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import NotFoundPage from '@/pages/NotFoundPage'
import { AuthProvider } from '@/auth/AuthContext'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { TooltipProvider } from '@/components/ui/tooltip'

import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage'

const DashboardPage      = lazy(() => import('@/pages/DashboardPage'))
const MarketOverviewPage = lazy(() => import('@/pages/MarketOverviewPage'))
const ExchangeDetailPage = lazy(() => import('@/pages/ExchangeDetailPage'))
const AssetDetailPage    = lazy(() => import('@/pages/AssetDetailPage'))
const WalletDetailPage   = lazy(() => import('@/pages/WalletDetailPage'))

function PageLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-base">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-edge border-t-accent" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <TooltipProvider>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login"    element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />

            <Route path="/market" element={<MarketOverviewPage />} />
            <Route path="/market/:exchangeCode" element={<ExchangeDetailPage />} />
            <Route path="/market/:exchangeCode/:ticker" element={<AssetDetailPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/wallets/:currencyCode" element={<WalletDetailPage />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
        </TooltipProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
