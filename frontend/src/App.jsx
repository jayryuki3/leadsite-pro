import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Discover from './pages/Discover'
import Leads from './pages/Leads'
import LeadDetail from './pages/LeadDetail'
import MockupBuilder from './pages/MockupBuilder'
import Outreach from './pages/Outreach'
import Settings from './pages/Settings'

export default function App() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/leads/:id" element={<LeadDetail />} />
          <Route path="/mockups" element={<MockupBuilder />} />
          <Route path="/mockups/:id" element={<MockupBuilder />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
