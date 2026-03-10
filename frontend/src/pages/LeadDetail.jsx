import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Globe, Phone, Mail, MapPin, Star, Shield, ShieldCheck,
  Search, Zap, Users, BarChart3, Loader2, ExternalLink, PaintBucket,
  RefreshCw, Save, Sparkles, ChevronDown, AlertCircle, Clock, FileText
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/client'

// ── Audit category config (same as Leads.jsx) ───────────────────
const AUDIT_CATEGORIES = [
  { key: 'https', label: 'HTTPS / Security', max: 15, icon: ShieldCheck },
  { key: 'mobile', label: 'Mobile Responsive', max: 20, icon: Globe },
  { key: 'seo', label: 'SEO Basics', max: 25, icon: Search },
  { key: 'structured_data', label: 'Structured Data', max: 10, icon: Zap },
  { key: 'social', label: 'Social Presence', max: 10, icon: Users },
  { key: 'page_size', label: 'Page Performance', max: 10, icon: BarChart3 },
  { key: 'content', label: 'Content Quality', max: 10, icon: Star },
]

const STATUSES = [
  { value: 'new', label: 'New' },
  { value: 'audited', label: 'Audited' },
  { value: 'prospect', label: 'Prospect' },
  { value: 'mockup_created', label: 'Mockup Created' },
  { value: 'mockup_sent', label: 'Mockup Sent' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'responded', label: 'Responded' },
  { value: 'closed_won', label: 'Closed Won' },
  { value: 'closed_lost', label: 'Closed Lost' },
]

const STATUS_COLORS = {
  new: 'bg-blue-100 text-blue-700',
  audited: 'bg-purple-100 text-purple-700',
  prospect: 'bg-amber-100 text-amber-700',
  mockup_created: 'bg-cyan-100 text-cyan-700',
  mockup_sent: 'bg-teal-100 text-teal-700',
  contacted: 'bg-orange-100 text-orange-700',
  responded: 'bg-green-100 text-green-700',
  closed_won: 'bg-emerald-100 text-emerald-700',
  closed_lost: 'bg-red-100 text-red-700',
}

// ── Score Bar ────────────────────────────────────────────────────
function ScoreBar({ score, max, label, icon: Icon }) {
  const pct = max > 0 ? Math.round((score / max) * 100) : 0
  let barColor = 'bg-red-500'
  if (pct >= 80) barColor = 'bg-emerald-500'
  else if (pct >= 50) barColor = 'bg-amber-500'
  else if (pct >= 25) barColor = 'bg-orange-500'

  return (
    <div className="flex items-center gap-2 text-sm">
      {Icon && <Icon className="w-4 h-4 text-gray-400 flex-shrink-0" />}
      <span className="w-36 text-gray-600">{label}</span>
      <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 text-right font-medium text-gray-700">{score}/{max}</span>
    </div>
  )
}

// ── Opportunity Badge ────────────────────────────────────────────
function OpportunityBadge({ score }) {
  if (!score && score !== 0) return <span className="text-gray-400 text-sm">Not ranked</span>
  let color = 'bg-red-100 text-red-700'
  let label = 'Low'
  if (score >= 70) { color = 'bg-emerald-100 text-emerald-700'; label = 'High' }
  else if (score >= 45) { color = 'bg-amber-100 text-amber-700'; label = 'Medium' }
  else if (score >= 25) { color = 'bg-orange-100 text-orange-700'; label = 'Low-Med' }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold ${color}`}>
      {Math.round(score)}/100 - {label}
    </span>
  )
}


export default function LeadDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [lead, setLead] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [status, setStatus] = useState('')
  const [updatingStatus, setUpdatingStatus] = useState(false)
  const [auditing, setAuditing] = useState(false)
  const [scraping, setScraping] = useState(false)

  useEffect(() => {
    loadLead()
  }, [id])

  const loadLead = async () => {
    try {
      setLoading(true)
      const res = await api.get(`/leads/${id}`)
      setLead(res.data)
      setNotes(res.data.notes || '')
      setStatus(res.data.status || 'new')
    } catch (err) {
      toast.error('Failed to load lead')
      navigate('/leads')
    } finally {
      setLoading(false)
    }
  }

  const saveNotes = async () => {
    try {
      setSavingNotes(true)
      await api.patch(`/leads/${id}/notes`, { notes })
      toast.success('Notes saved')
    } catch (err) {
      toast.error('Failed to save notes')
    } finally {
      setSavingNotes(false)
    }
  }

  const updateStatus = async (newStatus) => {
    try {
      setUpdatingStatus(true)
      await api.patch(`/leads/${id}/status`, { status: newStatus })
      setStatus(newStatus)
      setLead(prev => ({ ...prev, status: newStatus }))
      toast.success(`Status updated to ${newStatus.replace('_', ' ')}`)
    } catch (err) {
      toast.error('Failed to update status')
    } finally {
      setUpdatingStatus(false)
    }
  }

  const runAudit = async () => {
    try {
      setAuditing(true)
      toast('Running website audit...', { icon: '...' })
      await api.post(`/audit/${id}`)
      toast.success('Audit complete!')
      loadLead()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Audit failed'
      toast.error(msg)
    } finally {
      setAuditing(false)
    }
  }

  const runScrape = async () => {
    try {
      setScraping(true)
      toast('Scraping business info...', { icon: '...' })
      await api.post(`/leads/${id}/scrape`)
      toast.success('Enrichment complete!')
      loadLead()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Scrape failed'
      toast.error(msg)
    } finally {
      setScraping(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!lead) return null

  const auditDetails = lead.audit_details || {}
  const detail = lead.detail || {}
  const wqs = lead.website_quality_score
  const hasAudit = wqs !== undefined && wqs !== null && wqs >= 0

  return (
    <div className="h-full overflow-auto bg-gray-50">
      {/* ── Top Bar ─────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/leads')}
              className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{lead.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm text-gray-500 capitalize">{(lead.category || '').replace('_', ' ')}</span>
                <span className="text-gray-300">|</span>
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'}`}>
                  {(status || '').replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <OpportunityBadge score={lead.opportunity_score} />

            <button onClick={runScrape} disabled={scraping}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-1.5 disabled:opacity-50">
              {scraping ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Enrich
            </button>

            <button onClick={runAudit} disabled={auditing}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-1.5 disabled:opacity-50">
              {auditing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              {hasAudit ? 'Re-Audit' : 'Run Audit'}
            </button>

            <button onClick={() => navigate(`/mockups?lead=${lead.id}`)}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center gap-1.5">
              <PaintBucket className="w-4 h-4" />
              Generate Mockup
            </button>
          </div>
        </div>
      </div>

      {/* ── Main Content ────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-3 gap-6">

        {/* ── Left Column (2/3) ─────────────────────────────── */}
        <div className="col-span-2 space-y-6">

          {/* Contact & Info Card */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Contact Information</h2>
            <div className="grid grid-cols-2 gap-4">
              {lead.phone && (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center">
                    <Phone className="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Phone</p>
                    <a href={`tel:${lead.phone}`} className="text-sm font-medium text-gray-900 hover:text-blue-600">{lead.phone}</a>
                  </div>
                </div>
              )}
              {lead.email && (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center">
                    <Mail className="w-4 h-4 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Email</p>
                    <a href={`mailto:${lead.email}`} className="text-sm font-medium text-gray-900 hover:text-purple-600">{lead.email}</a>
                  </div>
                </div>
              )}
              {lead.website && (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center">
                    <Globe className="w-4 h-4 text-green-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Website</p>
                    <a href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                       target="_blank" rel="noopener noreferrer"
                       className="text-sm font-medium text-gray-900 hover:text-green-600 flex items-center gap-1">
                      {lead.website.replace(/^https?:\/\//, '').slice(0, 40)}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              )}
              {lead.address && (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-orange-50 rounded-lg flex items-center justify-center">
                    <MapPin className="w-4 h-4 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Address</p>
                    <p className="text-sm font-medium text-gray-900">{lead.address}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Google Maps + Rating row */}
            <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-100">
              {lead.google_maps_url && (
                <a href={lead.google_maps_url} target="_blank" rel="noopener noreferrer"
                   className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" /> View on Google Maps <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {lead.rating > 0 && (
                <div className="flex items-center gap-1.5 text-sm">
                  <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                  <span className="font-semibold text-gray-900">{lead.rating}</span>
                  <span className="text-gray-400">({lead.review_count} reviews)</span>
                </div>
              )}
            </div>
          </div>

          {/* Website Audit Card */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Website Audit</h2>
              {hasAudit && (
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-bold ${
                  wqs >= 80 ? 'bg-emerald-100 text-emerald-700' :
                  wqs >= 60 ? 'bg-green-100 text-green-700' :
                  wqs >= 40 ? 'bg-amber-100 text-amber-700' :
                  wqs >= 20 ? 'bg-orange-100 text-orange-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  Overall: {wqs}/100
                </span>
              )}
            </div>

            {hasAudit && Object.keys(auditDetails).length > 0 ? (
              <div className="space-y-3">
                {AUDIT_CATEGORIES.map(cat => (
                  <ScoreBar
                    key={cat.key}
                    score={auditDetails[cat.key] ?? 0}
                    max={cat.max}
                    label={cat.label}
                    icon={cat.icon}
                  />
                ))}
              </div>
            ) : hasAudit ? (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500">Audit score: {wqs}/100</p>
                <p className="text-xs text-gray-400 mt-1">Detailed breakdown not available for this audit</p>
              </div>
            ) : !lead.website ? (
              <div className="text-center py-6">
                <AlertCircle className="w-10 h-10 text-red-300 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-700">No website found</p>
                <p className="text-xs text-gray-400 mt-1">This is a high-opportunity lead -- they need a website!</p>
              </div>
            ) : (
              <div className="text-center py-6">
                <Shield className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Not audited yet</p>
                <button onClick={runAudit} disabled={auditing}
                  className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                  {auditing ? 'Auditing...' : 'Run Website Audit'}
                </button>
              </div>
            )}

            {/* Tech stack if available */}
            {detail.tech_stack && detail.tech_stack.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs text-gray-400 mb-2">Detected Tech Stack</p>
                <div className="flex flex-wrap gap-1.5">
                  {detail.tech_stack.map((tech, i) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">{tech}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Reviews Card */}
          {detail.top_reviews && detail.top_reviews.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Top Reviews</h2>
              <div className="space-y-4">
                {detail.top_reviews.slice(0, 5).map((review, i) => (
                  <div key={i} className="border-l-2 border-amber-300 pl-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">{review.user || 'Customer'}</span>
                      <div className="flex items-center gap-0.5">
                        {[...Array(review.rating || 5)].map((_, s) => (
                          <Star key={s} className="w-3 h-3 text-amber-400 fill-amber-400" />
                        ))}
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 leading-relaxed">{review.text || ''}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Profile Summary */}
          {detail.ai_profile_summary && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-500" /> AI Profile Summary
              </h2>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{detail.ai_profile_summary}</p>
            </div>
          )}
        </div>

        {/* ── Right Column (1/3) ────────────────────────────── */}
        <div className="space-y-6">

          {/* Pipeline Status */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Pipeline Status</h2>
            <select
              value={status}
              onChange={(e) => updateStatus(e.target.value)}
              disabled={updatingStatus}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STATUSES.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <div className="mt-3 flex flex-wrap gap-1">
              {STATUSES.map((s, i) => (
                <div key={s.value} className={`h-1.5 flex-1 rounded-full ${
                  STATUSES.findIndex(x => x.value === status) >= i
                    ? 'bg-blue-500'
                    : 'bg-gray-200'
                }`} />
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Quick Actions</h2>
            <div className="space-y-2">
              <button onClick={() => navigate(`/mockups?lead=${lead.id}`)}
                className="w-full px-3 py-2.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
                <PaintBucket className="w-4 h-4" /> Generate Mockup
              </button>
              <button onClick={runAudit} disabled={auditing}
                className="w-full px-3 py-2.5 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors disabled:opacity-50">
                <Shield className="w-4 h-4" /> {hasAudit ? 'Re-run Audit' : 'Run Website Audit'}
              </button>
              <button onClick={runScrape} disabled={scraping}
                className="w-full px-3 py-2.5 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors disabled:opacity-50">
                <RefreshCw className="w-4 h-4" /> Enrich / Scrape Data
              </button>
              {lead.website && (
                <a href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                   target="_blank" rel="noopener noreferrer"
                   className="w-full px-3 py-2.5 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
                  <ExternalLink className="w-4 h-4" /> Visit Website
                </a>
              )}
            </div>
          </div>

          {/* Business Details */}
          {(detail.services || detail.hours || detail.description) && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Business Details</h2>

              {detail.description && (
                <div className="mb-4">
                  <p className="text-xs text-gray-400 mb-1">Description</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{detail.description}</p>
                </div>
              )}

              {detail.services && detail.services.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-gray-400 mb-1.5">Services</p>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.services.map((svc, i) => (
                      <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{svc}</span>
                    ))}
                  </div>
                </div>
              )}

              {detail.hours && Object.keys(detail.hours).length > 0 && (
                <div>
                  <p className="text-xs text-gray-400 mb-1.5 flex items-center gap-1"><Clock className="w-3 h-3" /> Hours</p>
                  <div className="space-y-0.5">
                    {Object.entries(detail.hours).map(([day, hrs]) => (
                      <div key={day} className="flex justify-between text-xs">
                        <span className="text-gray-600 capitalize">{day}</span>
                        <span className="text-gray-900 font-medium">{hrs}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Notes */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Notes
            </h2>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes about this lead..."
              rows={5}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
            <button onClick={saveNotes} disabled={savingNotes}
              className="mt-2 w-full px-3 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-1.5 disabled:opacity-50">
              {savingNotes ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Notes
            </button>
          </div>

          {/* Timestamps */}
          <div className="text-xs text-gray-400 px-2 space-y-1">
            {lead.created_at && <p>Created: {new Date(lead.created_at).toLocaleDateString()}</p>}
            {lead.updated_at && <p>Updated: {new Date(lead.updated_at).toLocaleDateString()}</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
