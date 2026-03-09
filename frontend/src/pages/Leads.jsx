import { useState, useEffect } from 'react'
import { Users, Search, Filter, ArrowUpDown, Shield, ShieldAlert, ShieldCheck, Star, Globe, Sparkles, Loader2, BarChart3, Trash2, RefreshCw, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '../api/client'

// ── Score Badge Component ────────────────────────────────────────
function ScoreBadge({ score, label }) {
  let color = 'bg-gray-100 text-gray-600'
  if (score === -1) color = 'bg-gray-100 text-gray-400'
  else if (score === 0) color = 'bg-red-100 text-red-700'
  else if (score <= 30) color = 'bg-red-100 text-red-600'
  else if (score <= 60) color = 'bg-amber-100 text-amber-700'
  else if (score <= 80) color = 'bg-green-100 text-green-700'
  else color = 'bg-emerald-100 text-emerald-700'
  
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {score === -1 ? 'Not audited' : `${score}${label ? ` ${label}` : ''}`}
    </span>
  )
}

// ── Status Badge ─────────────────────────────────────────────────
function StatusBadge({ status }) {
  const styles = {
    new: 'bg-blue-100 text-blue-700',
    audited: 'bg-purple-100 text-purple-700',
    prospect: 'bg-amber-100 text-amber-700',
    mockup_created: 'bg-cyan-100 text-cyan-700',
    contacted: 'bg-orange-100 text-orange-700',
    responded: 'bg-green-100 text-green-700',
    converted: 'bg-emerald-100 text-emerald-700',
  }
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100 text-gray-600'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

export default function Leads() {
  const navigate = useNavigate()
  const [leads, setLeads] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [auditing, setAuditing] = useState(false)
  const [ranking, setRanking] = useState(false)
  const [aiLoading, setAiLoading] = useState({})
  const [aiResults, setAiResults] = useState({})
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('opportunity_score')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(0)
  const perPage = 25

  useEffect(() => {
    loadLeads()
  }, [statusFilter, categoryFilter, sortBy, sortOrder, page])

  const loadLeads = async () => {
    try {
      setLoading(true)
      const params = {
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: perPage,
        offset: page * perPage,
      }
      if (statusFilter) params.status = statusFilter
      if (categoryFilter) params.category = categoryFilter
      
      const res = await api.get('/leads', { params })
      setLeads(res.data.leads)
      setTotal(res.data.total)
    } catch (err) {
      toast.error('Failed to load leads')
    } finally {
      setLoading(false)
    }
  }

  const auditAll = async () => {
    try {
      setAuditing(true)
      const res = await api.post('/audit/batch', null, { params: { limit: 50 } })
      toast.success(`Audited ${res.data.audited} websites`)
      loadLeads()
    } catch (err) {
      toast.error('Audit failed')
    } finally {
      setAuditing(false)
    }
  }

  const rankAll = async () => {
    try {
      setRanking(true)
      const res = await api.post('/leads/rank')
      toast.success(`Ranked ${res.data.ranked} leads`)
      loadLeads()
    } catch (err) {
      toast.error('Ranking failed')
    } finally {
      setRanking(false)
    }
  }

  const auditSingle = async (leadId) => {
    try {
      setAiLoading(prev => ({ ...prev, [`audit_${leadId}`]: true }))
      await api.post(`/audit/${leadId}`)
      toast.success('Audit complete')
      loadLeads()
    } catch (err) {
      toast.error('Audit failed')
    } finally {
      setAiLoading(prev => ({ ...prev, [`audit_${leadId}`]: false }))
    }
  }

  const explainRanking = async (leadId) => {
    try {
      setAiLoading(prev => ({ ...prev, [`explain_${leadId}`]: true }))
      const res = await api.post(`/ai/explain-ranking/${leadId}`)
      setAiResults(prev => ({ ...prev, [leadId]: res.data.explanation }))
    } catch (err) {
      toast.error('AI explanation failed. Check OpenAI API key.')
    } finally {
      setAiLoading(prev => ({ ...prev, [`explain_${leadId}`]: false }))
    }
  }

  const analyzeAudit = async (leadId) => {
    try {
      setAiLoading(prev => ({ ...prev, [`analyze_${leadId}`]: true }))
      const res = await api.post(`/ai/analyze-audit/${leadId}`)
      setAiResults(prev => ({ ...prev, [`audit_${leadId}`]: res.data.analysis }))
    } catch (err) {
      toast.error('AI analysis failed')
    } finally {
      setAiLoading(prev => ({ ...prev, [`analyze_${leadId}`]: false }))
    }
  }

  const toggleSort = (col) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(col)
      setSortOrder('desc')
    }
    setPage(0)
  }

  const filteredLeads = searchQuery
    ? leads.filter(l => l.name.toLowerCase().includes(searchQuery.toLowerCase()) || l.category.includes(searchQuery.toLowerCase()))
    : leads

  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Users className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
            <p className="text-sm text-gray-500">{total} businesses ranked by opportunity score</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={auditAll} disabled={auditing}
            className="px-3 py-2 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg text-sm font-medium text-purple-700 flex items-center gap-1.5 disabled:opacity-50">
            {auditing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            Audit All
          </button>
          <button onClick={rankAll} disabled={ranking}
            className="px-3 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg text-sm font-medium text-blue-700 flex items-center gap-1.5 disabled:opacity-50">
            {ranking ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            Rank All
          </button>
          <button onClick={loadLeads}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search leads..." className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="audited">Audited</option>
          <option value="prospect">Prospect</option>
          <option value="mockup_created">Mockup Created</option>
          <option value="contacted">Contacted</option>
          <option value="responded">Responded</option>
          <option value="converted">Converted</option>
        </select>
        <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(0) }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">All Categories</option>
          <option value="electrician">Electrician</option>
          <option value="plumber">Plumber</option>
          <option value="contractor">Contractor</option>
          <option value="hvac">HVAC</option>
          <option value="dentist">Dentist</option>
          <option value="salon">Salon</option>
          <option value="auto_repair">Auto Repair</option>
          <option value="landscaper">Landscaper</option>
          <option value="restaurant">Restaurant</option>
        </select>
      </div>

      {/* Leads Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Business</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600"
                    onClick={() => toggleSort('rating')}>
                  <span className="inline-flex items-center gap-1">Rating <ArrowUpDown className="w-3 h-3" /></span>
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600"
                    onClick={() => toggleSort('website_quality_score')}>
                  <span className="inline-flex items-center gap-1">Website <ArrowUpDown className="w-3 h-3" /></span>
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-blue-600"
                    onClick={() => toggleSort('opportunity_score')}>
                  <span className="inline-flex items-center gap-1">Opportunity <ArrowUpDown className="w-3 h-3" /></span>
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600 mx-auto" />
                </td></tr>
              ) : filteredLeads.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-500">
                  No leads found. Go to Discover to scan for businesses.
                </td></tr>
              ) : filteredLeads.map(lead => (
                <tr key={lead.id} className="hover:bg-gray-50 group">
                  <td className="px-4 py-3">
                    <button onClick={() => navigate(`/leads/${lead.id}`)} className="text-left">
                      <div className="font-medium text-gray-900 group-hover:text-blue-600">{lead.name}</div>
                      <div className="text-xs text-gray-500 truncate max-w-[220px]">{lead.address}</div>
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex px-2 py-0.5 bg-gray-100 rounded text-xs">
                      {lead.category.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {lead.rating ? (
                      <span className="inline-flex items-center gap-1 text-sm">
                        <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                        {lead.rating}
                        <span className="text-gray-400 text-xs">({lead.review_count})</span>
                      </span>
                    ) : <span className="text-gray-400">-</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <ScoreBadge score={lead.website_quality_score} />
                      {lead.website ? (
                        <a href={lead.website} target="_blank" rel="noopener noreferrer"
                           className="text-xs text-blue-500 hover:underline inline-flex items-center gap-0.5">
                          <Globe className="w-3 h-3" /> visit
                        </a>
                      ) : (
                        <span className="text-xs text-red-500 font-medium">No website</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <span className="text-lg font-bold text-gray-900">
                        {lead.opportunity_score > 0 ? lead.opportunity_score.toFixed(1) : '-'}
                      </span>
                      <button
                        onClick={() => explainRanking(lead.id)}
                        disabled={aiLoading[`explain_${lead.id}`]}
                        className="text-xs text-purple-600 hover:text-purple-800 inline-flex items-center gap-0.5"
                      >
                        {aiLoading[`explain_${lead.id}`] ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                        Why?
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge status={lead.status} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      {lead.website_quality_score === -1 && (
                        <button onClick={() => auditSingle(lead.id)} disabled={aiLoading[`audit_${lead.id}`]}
                          className="p-1.5 hover:bg-purple-50 rounded text-purple-600" title="Audit website">
                          {aiLoading[`audit_${lead.id}`] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
                        </button>
                      )}
                      {lead.website_quality_score >= 0 && (
                        <button onClick={() => analyzeAudit(lead.id)} disabled={aiLoading[`analyze_${lead.id}`]}
                          className="p-1.5 hover:bg-blue-50 rounded text-blue-600" title="AI analysis">
                          {aiLoading[`analyze_${lead.id}`] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                        </button>
                      )}
                      {lead.google_maps_url && (
                        <a href={lead.google_maps_url} target="_blank" rel="noopener noreferrer"
                           className="p-1.5 hover:bg-gray-100 rounded text-gray-500" title="Google Maps">
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* AI Result Popups */}
        {Object.entries(aiResults).map(([key, text]) => (
          <div key={key} className="mx-4 mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-1.5 text-sm font-medium text-purple-700 mb-1">
                <Sparkles className="w-4 h-4" /> AI Analysis
              </div>
              <button onClick={() => setAiResults(prev => { const next = {...prev}; delete next[key]; return next })}
                className="text-purple-400 hover:text-purple-600 text-xs">dismiss</button>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{text}</p>
          </div>
        ))}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <span className="text-sm text-gray-500">
              Showing {page * perPage + 1}-{Math.min((page + 1) * perPage, total)} of {total}
            </span>
            <div className="flex gap-1">
              <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
                className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-50">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
                className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-50">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}