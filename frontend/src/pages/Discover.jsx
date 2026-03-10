import { useState, useEffect } from 'react'
import { Search, MapPin, Loader2, Plus, Filter, Globe, Star, Phone } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '../api/client'

const CATEGORIES = [
  { key: 'restaurant', label: 'Restaurants' },
  { key: 'cafe', label: 'Cafes & Bakeries' },
  { key: 'salon', label: 'Hair Salons' },
  { key: 'spa', label: 'Spas' },
  { key: 'gym', label: 'Gyms' },
  { key: 'dentist', label: 'Dentists' },
  { key: 'doctor', label: 'Doctors' },
  { key: 'lawyer', label: 'Lawyers' },
  { key: 'plumber', label: 'Plumbers' },
  { key: 'electrician', label: 'Electricians' },
  { key: 'roofing', label: 'Roofers' },
  { key: 'car_repair', label: 'Auto Repair' },
  { key: 'real_estate', label: 'Real Estate' },
  { key: 'accountant', label: 'Accountants' },
  { key: 'veterinarian', label: 'Veterinarians' },
  { key: 'bar', label: 'Bars & Nightlife' },
  { key: 'hotel', label: 'Hotels' },
  { key: 'florist', label: 'Florists' },
  { key: 'pet_store', label: 'Pet Stores' },
  { key: 'pharmacy', label: 'Pharmacies' },
]

export default function Discover() {
  const navigate = useNavigate()
  const [location, setLocation] = useState('')
  const [radius, setRadius] = useState(5000)
  const [selectedCategories, setSelectedCategories] = useState(['restaurant'])
  const [keyword, setKeyword] = useState('')
  const [scanning, setScanning] = useState(false)
  const [results, setResults] = useState(null)
  const [geolocating, setGeolocating] = useState(false)

  const toggleCategory = (key) => {
    setSelectedCategories(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported')
      return
    }
    setGeolocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation(`${pos.coords.latitude},${pos.coords.longitude}`)
        setGeolocating(false)
        toast.success('Location detected!')
      },
      () => {
        toast.error('Could not get location')
        setGeolocating(false)
      }
    )
  }

  const startScan = async () => {
    if (!location) return toast.error('Enter a location or use GPS')
    if (selectedCategories.length === 0) return toast.error('Select at least one category')
    try {
      setScanning(true)
      const res = await api.post('/leads/discover', {
        location,
        radius,
        categories: selectedCategories,
        keyword: keyword || undefined,
      })
      setResults(res.data)
      toast.success(`Found ${res.data.found} businesses!`)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Scan failed. Check your Google API key in Settings.'
      toast.error(msg)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Search className="w-8 h-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Discover Businesses</h1>
          <p className="text-sm text-gray-500">Find local businesses that need a better web presence</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="grid grid-cols-12 gap-4 mb-4">
          <div className="col-span-5">
            <label className="block text-xs font-medium text-gray-600 mb-1">Location</label>
            <div className="flex gap-2">
              <input type="text" value={location} onChange={(e) => setLocation(e.target.value)}
                placeholder="City, address, or lat,lng"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <button onClick={useMyLocation} disabled={geolocating}
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1 text-gray-700">
                {geolocating ? <Loader2 className="w-4 h-4 animate-spin" /> : <MapPin className="w-4 h-4" />}
                GPS
              </button>
            </div>
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Radius</label>
            <select value={radius} onChange={(e) => setRadius(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value={1000}>1 km</option>
              <option value={2000}>2 km</option>
              <option value={5000}>5 km</option>
              <option value={10000}>10 km</option>
              <option value={20000}>20 km</option>
              <option value={50000}>50 km</option>
            </select>
          </div>
          <div className="col-span-3">
            <label className="block text-xs font-medium text-gray-600 mb-1">Keyword (optional)</label>
            <input type="text" value={keyword} onChange={(e) => setKeyword(e.target.value)}
              placeholder="e.g. pizza, roofing"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="col-span-2 flex items-end">
            <button onClick={startScan} disabled={scanning}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50">
              {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {scanning ? 'Scanning...' : 'Scan Area'}
            </button>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-2">
            <Filter className="w-3.5 h-3.5 inline mr-1" />
            Categories ({selectedCategories.length} selected)
          </label>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(cat => (
              <button key={cat.key} onClick={() => toggleCategory(cat.key)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                  selectedCategories.includes(cat.key)
                    ? 'bg-blue-100 border-blue-300 text-blue-700'
                    : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                }`}>
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {results && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Found {results.found} Businesses</h2>
            <button onClick={() => navigate('/leads')}
              className="px-3 py-1.5 bg-green-50 hover:bg-green-100 border border-green-200 rounded-lg text-xs font-medium text-green-700">
              View All Leads &rarr;
            </button>
          </div>
          <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
            {results.businesses.map((biz, i) => (
              <div key={i} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                <div>
                  <p className="font-medium text-sm text-gray-900">{biz.name}</p>
                  <p className="text-xs text-gray-500">{biz.address}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                      {biz.category.replace('_', ' ')}
                    </span>
                    {biz.rating > 0 && (
                      <span className="text-xs text-gray-500 flex items-center gap-0.5">
                        <Star className="w-3 h-3 text-yellow-500" /> {biz.rating} ({biz.review_count})
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  {biz.website ? (
                    <span className="text-xs text-green-600 flex items-center gap-1">
                      <Globe className="w-3 h-3" /> Has website
                    </span>
                  ) : (
                    <span className="text-xs text-red-500 font-medium">No website!</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
