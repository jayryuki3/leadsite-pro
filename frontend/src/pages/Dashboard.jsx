import { useState, useEffect } from 'react'
import { LayoutDashboard, Users, Shield, PaintBucket, Mail, TrendingUp, Search, Sparkles, Clock, ArrowRight, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '../api/client'

// Stat Card
function StatCard({ icon: Icon, label, value, color, sub }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
      {sub && <p className="text-xs text-gray-400 mt-2">{sub}</p>}
    </div>
  )
}

// Funnel Bar
function FunnelBar({ stages }) {
  const max = Math.max(...stages.map(s => s.count), 1)
  return (
    <div className="space-y-2">
      {stages.map((stage, i) => (
        <div key={stage.stage} className="flex items-center gap-3">
          <span className="text-xs text-gray-600 w-20 text-right">{stage.stage}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full flex items-center justify-end pr-2 transition-all duration-500"
              style={{ width: `${Math.max((stage.count / max) * 100, stage.count > 0 ? 8 : 0)}%` }}
            >
              {stage.count > 0 && <span className="text-xs font-medium text-white">{stage.count}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadDashboard() }, [])

  const loadDashboard = async () => {
    try {
      setLoading(true)
      const [statsRes, activityRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dashboard/activity'),
      ])
      setStats(statsRes.data)
      setActivities(activityRes.data.activities)
    } catch (err) {
      console.error('Dashboard load failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const actionIcons = {
    scan_completed: Search,
    batch_audit_completed: Shield,
    ranking_completed: TrendingUp,
    lead_enriched: Users,
    mockup_generated: PaintBucket,
    email_drafted: Mail,
    email_sent: Mail,
  }

  if (loading) {
    return <div className="p-6 flex items-center justify-center h-full">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
    </div>
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-500">Your lead generation command center</p>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <StatCard icon={Users} label="Total Leads" value={stats?.total_leads || 0} color="bg-blue-500" sub={`${stats?.no_website || 0} without website`} />
        <StatCard icon={Shield} label="Audited" value={stats?.audited || 0} color="bg-purple-500" sub={`Avg score: ${stats?.avg_website_score || 0}/100`} />
        <StatCard icon={PaintBucket} label="Mockups" value={stats?.mockup_count || 0} color="bg-cyan-500" />
        <StatCard icon={Mail} label="Emails Sent" value={stats?.email_sent || 0} color="bg-green-500" sub={`${stats?.email_drafts || 0} drafts pending`} />
        <StatCard icon={TrendingUp} label="Converted" value={stats?.status_counts?.converted || 0} color="bg-emerald-500" />
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Funnel */}
        <div className="col-span-5 bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-4">Pipeline Funnel</h2>
          {stats?.funnel ? <FunnelBar stages={stats.funnel} /> : <p className="text-gray-400 text-sm">No data yet</p>}
        </div>

        {/* Quick Actions */}
        <div className="col-span-3 bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <button onClick={() => navigate('/discover')}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-blue-50 hover:bg-blue-100 rounded-lg text-sm font-medium text-blue-700">
              <span className="flex items-center gap-2"><Search className="w-4 h-4" /> New Scan</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button onClick={() => navigate('/mockups')}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-cyan-50 hover:bg-cyan-100 rounded-lg text-sm font-medium text-cyan-700">
              <span className="flex items-center gap-2"><PaintBucket className="w-4 h-4" /> Generate Mockups</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button onClick={() => navigate('/outreach')}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-green-50 hover:bg-green-100 rounded-lg text-sm font-medium text-green-700">
              <span className="flex items-center gap-2"><Mail className="w-4 h-4" /> Draft Emails</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button onClick={() => navigate('/leads')}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-purple-50 hover:bg-purple-100 rounded-lg text-sm font-medium text-purple-700">
              <span className="flex items-center gap-2"><TrendingUp className="w-4 h-4" /> View Rankings</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Top Categories */}
        <div className="col-span-4 bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-4">Top Categories</h2>
          {stats?.top_categories?.length > 0 ? (
            <div className="space-y-2">
              {stats.top_categories.map(cat => (
                <div key={cat.category} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">{cat.category}</span>
                  <span className="text-sm font-medium text-gray-900">{cat.count} leads</span>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-400 text-sm">No leads discovered yet</p>}
        </div>

        {/* Activity Feed */}
        <div className="col-span-12 bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-400" /> Recent Activity
          </h2>
          {activities.length > 0 ? (
            <div className="space-y-3">
              {activities.slice(0, 10).map(a => {
                const ActionIcon = actionIcons[a.action] || Clock
                return (
                  <div key={a.id} className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                      <ActionIcon className="w-4 h-4 text-gray-500" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-700">{a.description}</p>
                      <p className="text-xs text-gray-400">{a.created_at ? new Date(a.created_at).toLocaleString() : ''}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : <p className="text-gray-400 text-sm">No activity yet. Start by scanning for businesses!</p>}
        </div>
      </div>
    </div>
  )
}