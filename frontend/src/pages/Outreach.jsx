import { useState, useEffect } from 'react'
import { Mail, Loader2, Sparkles, Send, Trash2, Edit3, Users, ChevronDown, Eye, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/client'

export default function Outreach() {
  const [drafts, setDrafts] = useState([])
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [sending, setSending] = useState({})
  const [selectedDraft, setSelectedDraft] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [editSubject, setEditSubject] = useState('')
  const [editBody, setEditBody] = useState('')
  const [editRecipient, setEditRecipient] = useState('')
  
  // Batch mode
  const [batchLeads, setBatchLeads] = useState([])
  const [batchTone, setBatchTone] = useState('professional')
  const [showBatchPanel, setShowBatchPanel] = useState(false)
  
  // Single generate
  const [genLeadId, setGenLeadId] = useState('')
  const [genTone, setGenTone] = useState('professional')

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [draftsRes, leadsRes] = await Promise.all([
        api.get('/emails'),
        api.get('/leads', { params: { sort_by: 'opportunity_score', sort_order: 'desc', limit: 100 } }),
      ])
      setDrafts(draftsRes.data.drafts)
      setLeads(leadsRes.data.leads)
    } catch (err) {
      toast.error('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const generateSingle = async () => {
    if (!genLeadId) return toast.error('Select a lead')
    try {
      setGenerating(true)
      const res = await api.post(`/emails/generate/${genLeadId}`, { tone: genTone })
      toast.success('Email drafted!')
      setSelectedDraft(res.data)
      setEditSubject(res.data.subject)
      setEditBody(res.data.body_html)
      loadData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const generateBatch = async () => {
    if (batchLeads.length === 0) return toast.error('Select leads first')
    try {
      setGenerating(true)
      const res = await api.post('/emails/batch-generate', { lead_ids: batchLeads, tone: batchTone })
      toast.success(`Generated ${res.data.generated} emails!`)
      setShowBatchPanel(false)
      loadData()
    } catch (err) {
      toast.error('Batch generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const viewDraft = async (draftId) => {
    try {
      const res = await api.get(`/emails/${draftId}`)
      setSelectedDraft(res.data)
      setEditSubject(res.data.subject)
      setEditBody(res.data.body_html)
      setEditRecipient(res.data.recipient_email || '')
      setEditMode(false)
    } catch (err) {
      toast.error('Failed to load draft')
    }
  }

  const saveDraft = async () => {
    if (!selectedDraft) return
    try {
      await api.put(`/emails/${selectedDraft.id}`, {
        subject: editSubject,
        body_html: editBody,
        recipient_email: editRecipient,
      })
      toast.success('Draft saved!')
      setEditMode(false)
      loadData()
    } catch (err) {
      toast.error('Save failed')
    }
  }

  const sendDraft = async (draftId) => {
    try {
      setSending(prev => ({ ...prev, [draftId]: true }))
      await api.post(`/emails/${draftId}/send`)
      toast.success('Email sent!')
      loadData()
      if (selectedDraft?.id === draftId) setSelectedDraft(null)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Send failed')
    } finally {
      setSending(prev => ({ ...prev, [draftId]: false }))
    }
  }

  const deleteDraft = async (draftId) => {
    try {
      await api.delete(`/emails/${draftId}`)
      toast.success('Deleted')
      if (selectedDraft?.id === draftId) setSelectedDraft(null)
      loadData()
    } catch (err) {
      toast.error('Delete failed')
    }
  }

  const statusStyles = {
    draft: 'bg-gray-100 text-gray-700',
    sent: 'bg-green-100 text-green-700',
    bounced: 'bg-red-100 text-red-700',
    opened: 'bg-blue-100 text-blue-700',
    replied: 'bg-emerald-100 text-emerald-700',
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Mail className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Email Outreach</h1>
            <p className="text-sm text-gray-500">{drafts.length} drafts</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowBatchPanel(!showBatchPanel)}
            className="px-3 py-2 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg text-sm font-medium text-purple-700 flex items-center gap-1.5">
            <Users className="w-4 h-4" /> Batch Mode
          </button>
          <button onClick={loadData}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {/* Generate Bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center gap-3">
        <select value={genLeadId} onChange={(e) => setGenLeadId(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="">Select a lead to draft an email for...</option>
          {leads.map(l => (
            <option key={l.id} value={l.id}>{l.name} ({l.category.replace('_',' ')}) - {l.opportunity_score} pts</option>
          ))}
        </select>
        <select value={genTone} onChange={(e) => setGenTone(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <option value="professional">Professional</option>
          <option value="casual">Casual</option>
          <option value="friendly">Friendly</option>
        </select>
        <button onClick={generateSingle} disabled={generating || !genLeadId}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 disabled:opacity-50">
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Draft Email
        </button>
      </div>

      {/* Batch Panel */}
      {showBatchPanel && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-4">
          <h3 className="font-semibold text-purple-800 mb-2">Batch Generate Emails</h3>
          <div className="flex flex-wrap gap-2 mb-3 max-h-32 overflow-y-auto">
            {leads.filter(l => l.opportunity_score > 0).slice(0, 30).map(l => (
              <label key={l.id} className="flex items-center gap-1.5 bg-white px-2 py-1 rounded border border-purple-200 text-sm cursor-pointer">
                <input type="checkbox" checked={batchLeads.includes(l.id)}
                  onChange={(e) => {
                    if (e.target.checked) setBatchLeads(prev => [...prev, l.id])
                    else setBatchLeads(prev => prev.filter(id => id !== l.id))
                  }} className="rounded" />
                {l.name}
              </label>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <select value={batchTone} onChange={(e) => setBatchTone(e.target.value)}
              className="px-3 py-1.5 border border-purple-300 rounded-lg text-sm">
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="friendly">Friendly</option>
            </select>
            <button onClick={generateBatch} disabled={generating || batchLeads.length === 0}
              className="px-4 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {generating ? <Loader2 className="w-4 h-4 animate-spin inline mr-1" /> : null}
              Generate {batchLeads.length} Emails
            </button>
            <span className="text-xs text-purple-600">{batchLeads.length} selected</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Drafts List */}
        <div className="w-1/3 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-100 font-semibold text-sm text-gray-700">Drafts</div>
          <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
            {loading ? (
              <div className="p-8 text-center"><Loader2 className="w-6 h-6 animate-spin text-blue-600 mx-auto" /></div>
            ) : drafts.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">No drafts yet. Select a lead above to generate one.</div>
            ) : drafts.map(d => (
              <button key={d.id} onClick={() => viewDraft(d.id)}
                className={`w-full text-left px-4 py-3 hover:bg-gray-50 ${selectedDraft?.id === d.id ? 'bg-blue-50' : ''}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm text-gray-900 truncate">{d.lead_name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${statusStyles[d.status] || ''}`}>{d.status}</span>
                </div>
                <div className="text-xs text-gray-500 truncate mt-0.5">{d.subject}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Email Preview/Edit */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
          {selectedDraft ? (
            <>
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">Email Preview</span>
                  <button onClick={() => setEditMode(!editMode)}
                    className="p-1 hover:bg-gray-100 rounded text-gray-500"><Edit3 className="w-4 h-4" /></button>
                </div>
                <div className="flex items-center gap-2">
                  {selectedDraft.status === 'draft' && (
                    <button onClick={() => sendDraft(selectedDraft.id)} disabled={sending[selectedDraft.id] || !editRecipient}
                      className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-50">
                      {sending[selectedDraft.id] ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />} Send
                    </button>
                  )}
                  <button onClick={() => deleteDraft(selectedDraft.id)}
                    className="p-1.5 hover:bg-red-50 rounded text-red-500"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                {editMode ? (
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-medium text-gray-500">Recipient Email</label>
                      <input type="email" value={editRecipient} onChange={(e) => setEditRecipient(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="owner@business.com" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500">Subject</label>
                      <input type="text" value={editSubject} onChange={(e) => setEditSubject(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500">Body (HTML)</label>
                      <textarea value={editBody} onChange={(e) => setEditBody(e.target.value)} rows={15}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono" />
                    </div>
                    <button onClick={saveDraft}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium">Save Changes</button>
                  </div>
                ) : (
                  <div>
                    <div className="mb-3">
                      <span className="text-xs text-gray-500">To: </span>
                      <span className="text-sm">{editRecipient || <span className="text-amber-600">Set recipient email (click edit)</span>}</span>
                    </div>
                    <div className="mb-3">
                      <span className="text-xs text-gray-500">Subject: </span>
                      <span className="text-sm font-medium">{editSubject}</span>
                    </div>
                    <div className="border-t border-gray-200 pt-3">
                      <div dangerouslySetInnerHTML={{ __html: editBody }} className="prose prose-sm max-w-none" />
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Mail className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">Select a draft to preview or generate a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}