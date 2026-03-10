import { useState, useEffect, useRef } from 'react'
import { PaintBucket, Loader2, Sparkles, Eye, Code, Send, Download, ChevronDown, RefreshCw, ExternalLink } from 'lucide-react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '../api/client'

export default function MockupBuilder() {
  const { id: mockupIdParam } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const iframeRef = useRef(null)
  
  const [leads, setLeads] = useState([])
  const [mockups, setMockups] = useState([])
  const [selectedLead, setSelectedLead] = useState(null)
  const [selectedMockup, setSelectedMockup] = useState(null)
  const [htmlContent, setHtmlContent] = useState('')
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [aiEditing, setAiEditing] = useState(false)
  const [aiInstruction, setAiInstruction] = useState('')
  const [viewMode, setViewMode] = useState('split') // 'code', 'preview', 'split'
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (mockupIdParam) {
      loadMockup(parseInt(mockupIdParam))
    }
  }, [mockupIdParam])

  useEffect(() => {
    updatePreview()
  }, [htmlContent])

  const loadData = async () => {
    try {
      setLoading(true)
      const [leadsRes, mockupsRes] = await Promise.all([
        api.get('/leads', { params: { sort_by: 'opportunity_score', sort_order: 'desc', limit: 100 } }),
        api.get('/mockups'),
      ])
      setLeads(leadsRes.data.leads)
      setMockups(mockupsRes.data.mockups)
      // Auto-select lead from query param (e.g. /mockups?lead=123)
      const preselect = searchParams.get('lead')
      if (preselect) setSelectedLead(parseInt(preselect))
    } catch (err) {
      toast.error('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadMockup = async (mockupId) => {
    try {
      const res = await api.get(`/mockups/${mockupId}`)
      setSelectedMockup(res.data)
      setHtmlContent(res.data.html || '')
    } catch (err) {
      toast.error('Failed to load mockup')
    }
  }

  const generateMockup = async () => {
    if (!selectedLead) {
      toast.error('Select a lead first')
      return
    }
    try {
      setGenerating(true)
      // First scrape the lead for enriched data
      toast('Scraping business info...', { icon: '🔍' })
      try {
        await api.post(`/leads/${selectedLead}/scrape`)
      } catch (e) {
        // Continue even if scrape fails
      }
      
      toast('Generating AI mockup...', { icon: '🎨' })
      const res = await api.post(`/mockups/generate/${selectedLead}`)
      
      // Load the generated mockup
      await loadMockup(res.data.mockup_id)
      toast.success('Mockup generated!')
      loadData() // Refresh mockup list
    } catch (err) {
      const msg = err.response?.data?.detail || 'Generation failed. Check your OpenAI API key.'
      toast.error(msg)
    } finally {
      setGenerating(false)
    }
  }

  const saveHtml = async () => {
    if (!selectedMockup) return
    try {
      setSaving(true)
      await api.put(`/mockups/${selectedMockup.id}`, { html: htmlContent })
      toast.success('Saved!')
    } catch (err) {
      toast.error('Save failed')
    } finally {
      setSaving(false)
    }
  }

  const aiEdit = async () => {
    if (!selectedMockup || !aiInstruction.trim()) return
    try {
      setAiEditing(true)
      const res = await api.post(`/mockups/${selectedMockup.id}/ai-edit`, {
        instruction: aiInstruction,
      })
      setHtmlContent(res.data.html)
      setSelectedMockup(prev => ({ ...prev, version: res.data.version }))
      setAiInstruction('')
      toast.success(`v${res.data.version} - Applied: "${res.data.instruction_applied}"`)
      // Refresh mockup list so dropdown shows updated version
      const mockupsRes = await api.get('/mockups/')
      setMockups(mockupsRes.data.mockups)
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      toast.error('AI edit failed: ' + detail)
    } finally {
      setAiEditing(false)
    }
  }

  const updatePreview = () => {
    if (iframeRef.current && htmlContent) {
      const doc = iframeRef.current.contentDocument
      // Inject <base target="_self"> so all navigation stays inside the iframe
      let html = htmlContent
      if (html.includes('<head>')) {
        html = html.replace('<head>', '<head><base target="_self">')
      } else if (html.includes('<html>')) {
        html = html.replace('<html>', '<html><head><base target="_self"></head>')
      }
      doc.open()
      doc.write(html)
      doc.close()
    }
  }

  const downloadHtml = () => {
    if (!htmlContent) return
    const blob = new Blob([htmlContent], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mockup_${selectedMockup?.lead_id || 'draft'}.html`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return <div className="p-6 flex items-center justify-center h-full">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
    </div>
  }

  return (
    <div className="h-full flex flex-col">
      {/* Top Bar */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <PaintBucket className="w-6 h-6 text-blue-600" />
          <h1 className="text-lg font-bold text-gray-900">Mockup Builder</h1>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Lead Selector */}
          <select
            value={selectedLead || ''}
            onChange={(e) => setSelectedLead(e.target.value ? parseInt(e.target.value) : null)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm max-w-[250px]"
          >
            <option value="">Select a lead...</option>
            {leads.map(l => (
              <option key={l.id} value={l.id}>
                {l.name} ({l.category.replace('_',' ')}) - Score: {l.opportunity_score}
              </option>
            ))}
          </select>
          
          <button onClick={generateMockup} disabled={generating || !selectedLead}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 disabled:opacity-50">
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Generate
          </button>

          {/* Existing Mockups Dropdown */}
          {mockups.length > 0 && (
            <select
              value={selectedMockup?.id || ''}
              onChange={(e) => e.target.value && loadMockup(parseInt(e.target.value))}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm max-w-[200px]"
            >
              <option value="">Load mockup...</option>
              {mockups.map(m => (
                <option key={m.id} value={m.id}>
                  {m.lead_name} (v{m.version})
                </option>
              ))}
            </select>
          )}
          
          <div className="border-l border-gray-300 h-6 mx-1"></div>
          
          {/* View Mode Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            <button onClick={() => setViewMode('code')}
              className={`px-2.5 py-1 rounded text-xs font-medium ${viewMode === 'code' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}>
              <Code className="w-3.5 h-3.5" />
            </button>
            <button onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 rounded text-xs font-medium ${viewMode === 'split' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}>
              Split
            </button>
            <button onClick={() => setViewMode('preview')}
              className={`px-2.5 py-1 rounded text-xs font-medium ${viewMode === 'preview' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}>
              <Eye className="w-3.5 h-3.5" />
            </button>
          </div>
          
          <button onClick={saveHtml} disabled={saving || !selectedMockup}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 disabled:opacity-50">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
          </button>
          <button onClick={downloadHtml} disabled={!htmlContent}
            className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 disabled:opacity-50" title="Download HTML">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Code Editor */}
        {(viewMode === 'code' || viewMode === 'split') && (
          <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} flex flex-col border-r border-gray-200`}>
            <div className="bg-gray-800 px-3 py-1.5 text-xs text-gray-400 flex items-center justify-between">
              <span>HTML Editor</span>
              <span>{htmlContent.length.toLocaleString()} chars</span>
            </div>
            <textarea
              value={htmlContent}
              onChange={(e) => setHtmlContent(e.target.value)}
              className="flex-1 w-full p-4 font-mono text-sm bg-gray-900 text-green-400 resize-none focus:outline-none"
              spellCheck={false}
              placeholder="Generate a mockup or paste HTML here..."
            />
          </div>
        )}

        {/* Live Preview */}
        {(viewMode === 'preview' || viewMode === 'split') && (
          <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} flex flex-col`}>
            <div className="bg-gray-100 px-3 py-1.5 text-xs text-gray-500 flex items-center justify-between">
              <span>Live Preview</span>
              <button onClick={updatePreview} className="hover:text-gray-700">
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
            {htmlContent ? (
              <iframe
                ref={iframeRef}
                className="flex-1 w-full bg-white"
                title="Mockup Preview"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              />
            ) : (
              <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <PaintBucket className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">Select a lead and click Generate to create a mockup</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* AI Edit Bar */}
      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <div className="relative flex-1">
            <Sparkles className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-purple-400" />
            <input
              type="text"
              value={aiInstruction}
              onChange={(e) => setAiInstruction(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && aiEdit()}
              placeholder='AI Edit: "Make the hero section blue" or "Add a pricing table"...'
              className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              disabled={!selectedMockup}
            />
          </div>
          <button
            onClick={aiEdit}
            disabled={aiEditing || !selectedMockup || !aiInstruction.trim()}
            className="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
          >
            {aiEditing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Apply
          </button>
        </div>
      </div>
    </div>
  )
}