import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DataManagement from './pages/DataManagement'
import ForecastExecution from './pages/ForecastExecution'
import ForecastResults from './pages/ForecastResults'
import Accounting from './pages/Accounting'
import Settings from './pages/Settings'
import NotFound from './pages/NotFound'

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="data" element={<DataManagement />} />
          <Route path="forecast" element={<ForecastExecution />} />
          <Route path="forecast/results" element={<ForecastResults />} />
          <Route path="forecast/results/:forecastId" element={<ForecastResults />} />
          <Route path="accounting" element={<Accounting />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
      
      {/* Toast通知 */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  )
}

export default App