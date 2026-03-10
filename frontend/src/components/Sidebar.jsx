import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Search, Users, PaintBucket, Mail, Settings, Zap } from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/discover', icon: Search, label: 'Discover' },
  { to: '/leads', icon: Users, label: 'Leads' },
  { to: '/mockups', icon: PaintBucket, label: 'Mockups' },
  { to: '/outreach', icon: Mail, label: 'Outreach' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div className="px-5 py-5 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900 leading-none">LeadSite Pro</h1>
            <p className="text-[10px] text-gray-400 mt-0.5">Lead Gen + AI Builder</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <Icon className="w-4.5 h-4.5" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-gray-100">
        <p className="text-[10px] text-gray-400 text-center">v1.0.0</p>
      </div>
    </aside>
  )
}
