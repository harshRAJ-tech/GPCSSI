import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, FileSearch, LogOut, ShieldAlert, Search, Database, Network, ShieldCheck, Activity } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import axios from 'axios'
import cytoscape from 'cytoscape'
import { useRef } from 'react'
import EvidenceUpload from './pages/EvidenceUpload'

function Login({ setToken }: { setToken: (t: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)
      
      const res = await axios.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      
      const token = res.data.access_token
      sessionStorage.setItem('ciip_token', token)
      setToken(token)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.status === 401 ? 'Incorrect username or password.' : 'Sign-in failed.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <div className="glass w-full max-w-md rounded-2xl p-8 shadow-2xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-primary/20 grid place-items-center text-primary font-black">CI</div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-white">Cyber Investigation</h1>
            <p className="text-xs text-slate-400 -mt-0.5">Intelligence Platform</p>
          </div>
        </div>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-mono">Agent ID</label>
            <input 
              type="text" 
              required 
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full rounded-lg bg-panel border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-primary transition-colors" 
              placeholder="operator_7" 
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-mono">Passphrase</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full rounded-lg bg-panel border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-primary transition-colors" 
              placeholder="••••••••" 
            />
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <button type="submit" className="w-full rounded-lg bg-primary text-white font-semibold py-2.5 text-sm hover:opacity-90 transition mt-4">
            AUTHENTICATE
          </button>
        </form>
      </div>
    </div>
  )
}

function Sidebar({ handleLogout }: { handleLogout: () => void }) {
  const location = useLocation()
  
  const NavLink = ({ to, icon: Icon, label }: { to: string, icon: any, label: string }) => {
    const isActive = location.pathname === to
    return (
      <Link to={to} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-sm font-medium ${isActive ? 'bg-primary/20 text-primary' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
        <Icon className="h-4 w-4" /> {label}
      </Link>
    )
  }

  return (
    <aside className="w-64 bg-panel border-r border-white/5 flex flex-col overflow-y-auto">
      <div className="p-6 flex items-center gap-3 border-b border-white/5 sticky top-0 bg-panel z-10">
        <ShieldAlert className="text-primary h-8 w-8" />
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">CIIP Terminal</h1>
          <p className="text-[10px] text-accent font-mono">v1.0.0-SECURE</p>
        </div>
      </div>
      
      <div className="flex-1 p-4 space-y-6">
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 px-2">Investigation Officer</p>
          <div className="space-y-1">
            <NavLink to="/dashboard" icon={LayoutDashboard} label="Command Center" />
            <NavLink to="/evidence" icon={Database} label="Evidence Upload" />
            <NavLink to="/search" icon={Search} label="Search Core" />
          </div>
        </div>

        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 px-2">Threat Analyst</p>
          <div className="space-y-1">
            <NavLink to="/graph" icon={Network} label="Graph Intelligence" />
            <NavLink to="/clustering" icon={Activity} label="Fraud Clustering (V2)" />
          </div>
        </div>

        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 px-2">DFIR Consultant</p>
          <div className="space-y-1">
            <NavLink to="/chain" icon={ShieldCheck} label="Chain of Custody" />
            <NavLink to="/audit" icon={FileSearch} label="Forensic Audit Trail" />
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-white/5 sticky bottom-0 bg-panel">
        <div className="mb-4 px-2">
          <div className="text-[10px] text-slate-500 font-mono">Current User:</div>
          <div className="text-xs text-white font-medium">SYS_ADMIN</div>
        </div>
        <button onClick={handleLogout} className="flex items-center gap-3 px-3 py-2 text-rose-400 hover:text-rose-300 hover:bg-rose-400/10 rounded-lg transition-colors w-full text-sm font-medium">
          <LogOut className="h-4 w-4" /> Disconnect Session
        </button>
      </div>
    </aside>
  )
}

function PlaceholderPage({ title, handleLogout }: { title: string, handleLogout: () => void }) {
  return (
    <div className="flex h-screen bg-background text-slate-300 font-sans overflow-hidden">
      <Sidebar handleLogout={handleLogout} />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-20 border-b border-white/5 flex items-center px-8 bg-panel/50 backdrop-blur-md sticky top-0 z-10">
          <h2 className="text-white font-semibold text-lg">{title}</h2>
        </header>
        <div className="p-8 flex items-center justify-center flex-1">
          <div className="glass p-12 rounded-3xl text-center max-w-lg">
            <ShieldAlert className="h-16 w-16 text-primary mx-auto mb-6 opacity-50" />
            <h3 className="text-xl font-bold text-white mb-2">{title} Module</h3>
            <p className="text-slate-400 text-sm">This module is currently offline or pending integration in the next deployment phase. Refer to the CIIP Architecture documentation for expected capabilities.</p>
          </div>
        </div>
      </main>
    </div>
  )
}

function Dashboard({ token, setToken }: { token: string, setToken: (t: string | null) => void }) {
  const [stats, setStats] = useState<any>(null)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/dashboard/stats', {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => setStats(res.data))
    .catch(err => {
      if (err.response?.status === 401) {
        sessionStorage.removeItem('ciip_token')
        setToken(null)
        navigate('/login')
      }
    })
  }, [token, navigate, setToken])

  const handleLogout = () => {
    sessionStorage.removeItem('ciip_token')
    setToken(null)
    navigate('/login')
  }

  if (!stats) return <div className="h-screen w-screen grid place-items-center bg-background text-accent">Initializing Intelligence Core...</div>

  const COLORS = ['#00f3ff', '#b026ff', '#00ff9d', '#ff3366', '#fcd34d']

  return (
    <div className="flex h-screen bg-background text-slate-300 font-sans overflow-hidden">
      <Sidebar handleLogout={handleLogout} />

      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-20 border-b border-white/5 flex items-center px-8 justify-between bg-panel/50 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 bg-primary/20 rounded-full grid place-items-center font-bold text-primary">CI</div>
            <div>
              <h2 className="text-white font-semibold">Command Center</h2>
              <p className="text-xs text-slate-400">Security is a process, not a product.</p>
            </div>
          </div>
        </header>

        <div className="p-8 space-y-6">
          <div className="grid grid-cols-4 gap-6">
            <div className="glass p-6 rounded-2xl flex flex-col gap-2">
              <span className="text-sm text-slate-400">Total Cases</span>
              <span className="text-3xl font-bold text-white">{stats.overview.total_cases}</span>
            </div>
            <div className="glass p-6 rounded-2xl flex flex-col gap-2">
              <span className="text-sm text-slate-400">Total Evidence Files</span>
              <span className="text-3xl font-bold text-accent">{stats.overview.total_evidence}</span>
            </div>
            <div className="glass p-6 rounded-2xl flex flex-col gap-2">
              <span className="text-sm text-slate-400">Entities Extracted</span>
              <span className="text-3xl font-bold text-[#b026ff]">{stats.overview.total_entities}</span>
            </div>
            <div className="glass p-6 rounded-2xl flex flex-col gap-2">
              <span className="text-sm text-slate-400">System Status</span>
              <span className="text-3xl font-bold text-success">SECURE</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-2 glass p-6 rounded-2xl">
              <h3 className="text-lg font-semibold text-white mb-6">Threat Summary (Last 30 Days)</h3>
              <div className="h-72 w-full">
                <ResponsiveContainer>
                  <LineChart data={stats.trend}>
                    <XAxis dataKey="date" stroke="#334155" fontSize={12} />
                    <YAxis stroke="#334155" fontSize={12} />
                    <Tooltip contentStyle={{ backgroundColor: '#151720', borderColor: '#334155' }} />
                    <Line type="monotone" dataKey="cases" stroke="#b026ff" strokeWidth={3} dot={{ fill: '#b026ff', r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl">
              <h3 className="text-lg font-semibold text-white mb-6">Threats By Type</h3>
              <div className="h-64 w-full relative">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={stats.entity_breakdown} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                      {stats.entity_breakdown.map((_entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#151720', borderColor: '#334155' }} />
                  </PieChart>
                </ResponsiveContainer>
                {stats.entity_breakdown.length === 0 && (
                  <div className="absolute inset-0 grid place-items-center text-sm text-slate-500">No data</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function SearchCore({ token, setToken }: { token: string, setToken: (t: string | null) => void }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any>(null)
  const [status, setStatus] = useState('')
  const cyRef = useRef<HTMLDivElement>(null)
  const cyInstance = useRef<any>(null)
  const navigate = useNavigate()

  const handleLogout = () => {
    sessionStorage.removeItem('ciip_token')
    setToken(null)
    navigate('/login')
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query) return
    setStatus('Correlating Intelligence...')
    setResults(null)
    if (cyInstance.current) {
      cyInstance.current.destroy()
      cyInstance.current = null
    }
    
    try {
      const res = await axios.get(`/search?value=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setStatus('')
      setResults(res.data)
    } catch (err: any) {
      if (err.response?.status === 401) handleLogout()
      else if (err.response?.status === 404) setStatus('No entities found for that value.')
      else setStatus('Search failed. Server error.')
    }
  }

  useEffect(() => {
    if (!results || !cyRef.current) return
    if (cyInstance.current) cyInstance.current.destroy()

    const elements: any[] = []
    const rootId = 'root'
    
    // Core Node
    elements.push({ data: { id: rootId, label: results.normalized_value, kind: 'root' } })

    // Linked Cases
    ;(results.cases || []).forEach((c: any) => {
      const id = 'case-' + c.case_id
      elements.push({ data: { id, label: '#' + c.case_id, kind: 'case' } })
      elements.push({ data: { id: 'e-' + id, source: rootId, target: id } })
    })

    // Linked Entities
    ;(results.connected_entities || []).forEach((c: any) => {
      const id = 'ent-' + c.entity_id
      elements.push({ data: { id, label: c.normalized_value, kind: 'entity' } })
      elements.push({ data: { id: 'e-' + id, source: rootId, target: id } })
    })

    cyInstance.current = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        { selector: 'node', style: { 'background-color': '#1f2937', 'label': 'data(label)', 'color': '#00f3ff', 'font-size': '10px', 'text-valign': 'bottom', 'text-margin-y': 4 } },
        { selector: 'node[kind="root"]', style: { 'background-color': '#00f3ff', 'color': '#fff', 'width': 40, 'height': 40 } },
        { selector: 'node[kind="case"]', style: { 'shape': 'round-rectangle', 'background-color': '#b026ff', 'color': '#fff' } },
        { selector: 'edge', style: { 'line-color': '#334155', 'curve-style': 'bezier' } },
      ],
      layout: { name: 'concentric', minNodeSpacing: 50 }
    })
    
    return () => {
      if (cyInstance.current) {
        cyInstance.current.destroy()
        cyInstance.current = null
      }
    }
  }, [results])

  return (
    <div className="flex h-screen bg-background text-slate-300 font-sans overflow-hidden">
      <Sidebar handleLogout={handleLogout} />
      
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-20 border-b border-white/5 flex items-center px-8 bg-panel/50 backdrop-blur-md sticky top-0 z-10">
          <h2 className="text-white font-semibold flex items-center gap-2"><Search className="text-accent" /> Investigation Map</h2>
        </header>

        <div className="p-8 flex flex-col items-center flex-1">
          <form onSubmit={handleSearch} className="w-full max-w-2xl relative mb-8">
            <input 
              type="text" 
              value={query} 
              onChange={e => setQuery(e.target.value)} 
              placeholder="Query entities (phone, upi, bank_account)..." 
              className="w-full bg-panel border border-accent/30 rounded-full px-6 py-4 text-base focus:outline-none focus:border-accent text-white shadow-[0_0_15px_rgba(0,243,255,0.1)] transition-all" 
            />
            <button type="submit" className="absolute right-2 top-2 bottom-2 bg-accent/20 text-accent px-6 rounded-full font-bold hover:bg-accent/40 transition-colors">
              EXECUTE
            </button>
          </form>

          {status && <div className="text-accent mb-4 animate-pulse">{status}</div>}

          {results && (
            <div className="w-full h-[600px] glass rounded-2xl border border-accent/30 p-4 relative flex flex-col">
              <h3 className="text-accent font-bold uppercase tracking-widest absolute top-4 left-4 z-10">Network Topology: {results.normalized_value}</h3>
              <div ref={cyRef} className="w-full h-full" />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function App() {
  const [token, setToken] = useState<string | null>(sessionStorage.getItem('ciip_token'))

  return (
    <Routes>
      <Route path="/login" element={token ? <Navigate to="/dashboard" /> : <Login setToken={setToken} />} />
      <Route path="/dashboard" element={token ? <Dashboard token={token} setToken={setToken} /> : <Navigate to="/login" />} />
      <Route path="/search" element={token ? <SearchCore token={token} setToken={setToken} /> : <Navigate to="/login" />} />
      <Route path="/evidence" element={token ? <EvidenceUpload token={token} handleLogout={() => {sessionStorage.removeItem('ciip_token'); setToken(null)}} Sidebar={Sidebar} /> : <Navigate to="/login" />} />
      <Route path="/graph" element={token ? <PlaceholderPage title="Graph Intelligence" handleLogout={() => {sessionStorage.removeItem('ciip_token'); setToken(null)}} /> : <Navigate to="/login" />} />
      <Route path="/clustering" element={token ? <PlaceholderPage title="Fraud Clustering" handleLogout={() => {sessionStorage.removeItem('ciip_token'); setToken(null)}} /> : <Navigate to="/login" />} />
      <Route path="/chain" element={token ? <PlaceholderPage title="Chain of Custody" handleLogout={() => {sessionStorage.removeItem('ciip_token'); setToken(null)}} /> : <Navigate to="/login" />} />
      <Route path="/audit" element={token ? <PlaceholderPage title="Forensic Audit Trail" handleLogout={() => {sessionStorage.removeItem('ciip_token'); setToken(null)}} /> : <Navigate to="/login" />} />
      <Route path="/" element={<Navigate to={token ? "/dashboard" : "/login"} />} />
    </Routes>
  )
}

export default App
