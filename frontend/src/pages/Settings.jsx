import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Key, Building2, MapPin, DollarSign, Mail, Eye, EyeOff, CheckCircle, XCircle, Loader2, Save, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/client'

// ── Section Component ────────────────────────────────────────────
function SettingsSection({ title, icon: Icon, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        </div>
        {open ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </button>
      {open && <div className="px-5 pb-5 border-t border-gray-100 pt-4">{children}</div>}
    </div>
  )
}

// ── Password Input with Toggle ───────────────────────────────────
function SecretInput({ label, value, onChange, placeholder, onTest, testLoading, testResult }) {
  const [show, setShow] = useState(false)
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={show ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
          />
          <button
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {onTest && (
          <button
            onClick={onTest}
            disabled={testLoading || !value}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 disabled:opacity-50 flex items-center gap-1"
          >
            {testLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 
             testResult === true ? <CheckCircle className="w-4 h-4 text-green-500" /> :
             testResult === false ? <XCircle className="w-4 h-4 text-red-500" /> : null}
            Test
          </button>
        )}
      </div>
    </div>
  )
}

// ── Text Input ───────────────────────────────────────────────────
function TextInput({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  )
}

// ── Pricing Tier Card ────────────────────────────────────────────
function PricingTierCard({ tier, onChange }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">{tier.display_name}</h3>
        <div className="flex items-center gap-1">
          <span className="text-gray-500 text-sm">$</span>
          <input
            type="number"
            value={tier.price}
            onChange={(e) => onChange({ ...tier, price: parseFloat(e.target.value) || 0 })}
            className="w-24 px-2 py-1 border border-gray-300 rounded text-sm font-bold text-right"
          />
          <span className="text-gray-500 text-sm">{tier.price_type === 'monthly' ? '/mo' : ' flat'}</span>
        </div>
      </div>
      <input
        type="text"
        value={tier.description}
        onChange={(e) => onChange({ ...tier, description: e.target.value })}
        className="w-full px-2 py-1 border border-gray-200 rounded text-sm text-gray-600"
      />
      <div>
        <label className="text-xs font-medium text-gray-500 uppercase">Features (one per line)</label>
        <textarea
          value={tier.features.join('\n')}
          onChange={(e) => onChange({ ...tier, features: e.target.value.split('\n').filter(Boolean) })}
          rows={tier.features.length + 1}
          className="w-full px-2 py-1 border border-gray-200 rounded text-sm mt-1"
        />
      </div>
    </div>
  )
}

// ── Main Settings Page ───────────────────────────────────────────
export default function Settings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testResults, setTestResults] = useState({})
  const [testLoading, setTestLoading] = useState({})
  
  // API Keys
  const [googleKey, setGoogleKey] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [openaiModel, setOpenaiModel] = useState('gpt-4o')
  const [yelpKey, setYelpKey] = useState('')
  const [availableModels, setAvailableModels] = useState(['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'])
  
  // Business Info
  const [bizName, setBizName] = useState('')
  const [bizEmail, setBizEmail] = useState('')
  const [bizPhone, setBizPhone] = useState('')
  const [bizWebsite, setBizWebsite] = useState('')
  const [calendlyLink, setCalendlyLink] = useState('')
  
  // Search Config
  const [searchLat, setSearchLat] = useState('37.7749')
  const [searchLng, setSearchLng] = useState('-122.4194')
  const [searchRadius, setSearchRadius] = useState('10')
  const [searchZip, setSearchZip] = useState('')
  
  // Email/SMTP
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState('587')
  const [smtpUser, setSmtpUser] = useState('')
  const [smtpPass, setSmtpPass] = useState('')
  const [smtpFromName, setSmtpFromName] = useState('')
  const [smtpFromEmail, setSmtpFromEmail] = useState('')
  
  // Pricing
  const [pricingTiers, setPricingTiers] = useState([])

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const [settingsRes, pricingRes, modelsRes] = await Promise.all([
        api.get('/settings'),
        api.get('/settings/pricing'),
        api.get('/settings/openai-models'),
      ])
      
      const s = settingsRes.data.settings
      
      // API Keys - show placeholder if has_value
      if (s.api_keys) {
        setGoogleKey(s.api_keys.google_places_api_key?.has_value ? '' : '')
        setOpenaiKey(s.api_keys.openai_api_key?.has_value ? '' : '')
        setOpenaiModel(s.api_keys.openai_model?.value || 'gpt-4o')
        setYelpKey(s.api_keys.yelp_api_key?.has_value ? '' : '')
      }
      
      // Business Info
      if (s.business_info) {
        setBizName(s.business_info.business_name?.value || '')
        setBizEmail(s.business_info.business_email?.value || '')
        setBizPhone(s.business_info.business_phone?.value || '')
        setBizWebsite(s.business_info.business_website?.value || '')
        setCalendlyLink(s.business_info.calendly_link?.value || '')
      }
      
      // Search Config
      if (s.search) {
        setSearchLat(s.search.search_latitude?.value || '37.7749')
        setSearchLng(s.search.search_longitude?.value || '-122.4194')
        setSearchRadius(s.search.search_radius_miles?.value || '10')
        setSearchZip(s.search.search_zip_code?.value || '')
      }
      
      // SMTP
      if (s.email) {
        setSmtpHost(s.email.smtp_host?.value || '')
        setSmtpPort(s.email.smtp_port?.value || '587')
        setSmtpUser(s.email.smtp_username?.value || '')
        setSmtpPass(s.email.smtp_password?.has_value ? '' : '')
        setSmtpFromName(s.email.smtp_from_name?.value || '')
        setSmtpFromEmail(s.email.smtp_from_email?.value || '')
      }
      
      // Pricing
      setPricingTiers(pricingRes.data.tiers)
      setAvailableModels(modelsRes.data.models)
    } catch (err) {
      console.error('Failed to load settings:', err)
      toast.error('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const saveAllSettings = async () => {
    try {
      setSaving(true)
      
      const updates = {
        openai_model: openaiModel,
        business_name: bizName,
        business_email: bizEmail,
        business_phone: bizPhone,
        business_website: bizWebsite,
        calendly_link: calendlyLink,
        search_latitude: searchLat,
        search_longitude: searchLng,
        search_radius_miles: searchRadius,
        search_zip_code: searchZip,
        smtp_host: smtpHost,
        smtp_port: smtpPort,
        smtp_username: smtpUser,
        smtp_from_name: smtpFromName,
        smtp_from_email: smtpFromEmail,
      }
      
      // Only include API keys if user entered new values
      if (googleKey) updates.google_places_api_key = googleKey
      if (openaiKey) updates.openai_api_key = openaiKey
      if (yelpKey) updates.yelp_api_key = yelpKey
      if (smtpPass) updates.smtp_password = smtpPass
      
      await api.put('/settings', { settings: updates })
      
      // Save pricing tiers
      await api.put('/settings/pricing', pricingTiers)
      
      toast.success('Settings saved successfully!')
    } catch (err) {
      console.error('Save failed:', err)
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const testApiKey = async (provider) => {
    try {
      setTestLoading(prev => ({ ...prev, [provider]: true }))
      setTestResults(prev => ({ ...prev, [provider]: null }))
      
      // Save the key first if user entered a new one
      const keyMap = {
        google_places: { key: 'google_places_api_key', value: googleKey },
        openai: { key: 'openai_api_key', value: openaiKey },
        yelp: { key: 'yelp_api_key', value: yelpKey },
      }
      
      if (keyMap[provider]?.value) {
        await api.put(`/settings/${keyMap[provider].key}`, { value: keyMap[provider].value })
      }
      
      const res = await api.post(`/settings/test/${provider}`)
      setTestResults(prev => ({ ...prev, [provider]: res.data.valid }))
      
      if (res.data.valid) {
        toast.success(`${provider} API key is valid!`)
      } else {
        toast.error(`${provider} API key is invalid`)
      }
    } catch (err) {
      setTestResults(prev => ({ ...prev, [provider]: false }))
      toast.error(`Failed to test ${provider} key`)
    } finally {
      setTestLoading(prev => ({ ...prev, [provider]: false }))
    }
  }

  const updatePricingTier = (index, updated) => {
    const newTiers = [...pricingTiers]
    newTiers[index] = updated
    setPricingTiers(newTiers)
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="text-sm text-gray-500">Configure API keys, pricing, and preferences</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadSettings}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reload
          </button>
          <button
            onClick={saveAllSettings}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save All Settings
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* API Keys */}
        <SettingsSection title="API Keys" icon={Key} defaultOpen={true}>
          <div className="space-y-4">
            <SecretInput
              label="Google Places API Key"
              value={googleKey}
              onChange={setGoogleKey}
              placeholder="AIza..."
              onTest={() => testApiKey('google_places')}
              testLoading={testLoading.google_places}
              testResult={testResults.google_places}
            />
            <SecretInput
              label="OpenAI API Key"
              value={openaiKey}
              onChange={setOpenaiKey}
              placeholder="sk-..."
              onTest={() => testApiKey('openai')}
              testLoading={testLoading.openai}
              testResult={testResults.openai}
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">OpenAI Model</label>
              <select
                value={openaiModel}
                onChange={(e) => setOpenaiModel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {availableModels.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <SecretInput
              label="Yelp Fusion API Key (Optional)"
              value={yelpKey}
              onChange={setYelpKey}
              placeholder="Bearer token..."
              onTest={() => testApiKey('yelp')}
              testLoading={testLoading.yelp}
              testResult={testResults.yelp}
            />
          </div>
        </SettingsSection>

        {/* Business Info */}
        <SettingsSection title="Your Business Info" icon={Building2}>
          <div className="grid grid-cols-2 gap-4">
            <TextInput label="Business Name" value={bizName} onChange={setBizName} placeholder="Your Web Design Co." />
            <TextInput label="Email" value={bizEmail} onChange={setBizEmail} placeholder="you@example.com" type="email" />
            <TextInput label="Phone" value={bizPhone} onChange={setBizPhone} placeholder="(555) 123-4567" />
            <TextInput label="Website" value={bizWebsite} onChange={setBizWebsite} placeholder="https://yoursite.com" />
            <div className="col-span-2">
              <TextInput label="Calendly / Booking Link" value={calendlyLink} onChange={setCalendlyLink} placeholder="https://calendly.com/yourname" />
            </div>
          </div>
        </SettingsSection>

        {/* Search Configuration */}
        <SettingsSection title="Search Location" icon={MapPin}>
          <div className="grid grid-cols-2 gap-4">
            <TextInput label="Zip Code" value={searchZip} onChange={setSearchZip} placeholder="94105" />
            <TextInput label="Search Radius (miles)" value={searchRadius} onChange={setSearchRadius} placeholder="10" type="number" />
            <TextInput label="Latitude" value={searchLat} onChange={setSearchLat} placeholder="37.7749" />
            <TextInput label="Longitude" value={searchLng} onChange={setSearchLng} placeholder="-122.4194" />
          </div>
          <p className="text-xs text-gray-500 mt-3">
            Enter a zip code or lat/lng coordinates. The Discover page will search for businesses within the specified radius.
          </p>
        </SettingsSection>

        {/* Email / SMTP */}
        <SettingsSection title="Email Configuration (SMTP)" icon={Mail}>
          <div className="grid grid-cols-2 gap-4">
            <TextInput label="SMTP Host" value={smtpHost} onChange={setSmtpHost} placeholder="smtp.gmail.com" />
            <TextInput label="SMTP Port" value={smtpPort} onChange={setSmtpPort} placeholder="587" />
            <TextInput label="SMTP Username" value={smtpUser} onChange={setSmtpUser} placeholder="you@gmail.com" />
            <SecretInput label="SMTP Password" value={smtpPass} onChange={setSmtpPass} placeholder="App password..." />
            <TextInput label="From Name" value={smtpFromName} onChange={setSmtpFromName} placeholder="Jay at LeadSite Pro" />
            <TextInput label="From Email" value={smtpFromEmail} onChange={setSmtpFromEmail} placeholder="you@gmail.com" type="email" />
          </div>
          <p className="text-xs text-gray-500 mt-3">
            For Gmail: use an App Password (Settings → Security → 2-Step → App Passwords). Host: smtp.gmail.com, Port: 587.
          </p>
        </SettingsSection>

        {/* Pricing Tiers */}
        <SettingsSection title="Pricing Tiers" icon={DollarSign}>
          <div className="space-y-4">
            {pricingTiers.map((tier, i) => (
              <PricingTierCard
                key={tier.name}
                tier={tier}
                onChange={(updated) => updatePricingTier(i, updated)}
              />
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            These pricing tiers will be shown in outreach emails. Adjust prices and features to match your market.
          </p>
        </SettingsSection>
      </div>

      {/* Bottom Save Bar */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 -mx-6 px-6 py-3 mt-6 flex justify-end">
        <button
          onClick={saveAllSettings}
          disabled={saving}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50 shadow-sm"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save All Settings
        </button>
      </div>
    </div>
  )
}