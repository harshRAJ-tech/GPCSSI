import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { UploadCloud, CheckCircle, AlertCircle, Database } from 'lucide-react'

export default function EvidenceUpload({ token, handleLogout, Sidebar }: { token: string, handleLogout: () => void, Sidebar: any }) {
  const [cases, setCases] = useState<any[]>([])
  const [selectedCase, setSelectedCase] = useState<string>('')
  const [files, setFiles] = useState<File[]>([])
  const [status, setStatus] = useState<string>('')
  const [results, setResults] = useState<any[]>([])

  useEffect(() => {
    axios.get('/cases', { headers: { Authorization: `Bearer ${token}` } })
      .then(res => setCases(res.data))
      .catch(err => {
        if (err.response?.status === 401) handleLogout()
      })
  }, [token, handleLogout])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleUpload = async () => {
    if (!selectedCase || files.length === 0) {
      setStatus('Please select a case and at least one file.')
      return
    }

    setStatus('Uploading and extracting intelligence...')
    setResults([])

    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      
      try {
        const res = await axios.post(`/cases/${selectedCase}/evidence`, formData, {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        })
        setResults(prev => [...prev, res.data])
      } catch (err: any) {
        setStatus(`Error uploading ${file.name}: ${err.response?.data?.detail || 'Unknown error'}`)
        return
      }
    }

    setStatus('Upload and extraction complete.')
    setFiles([])
  }

  return (
    <div className="flex h-screen bg-background text-slate-300 font-sans overflow-hidden">
      <Sidebar handleLogout={handleLogout} />
      
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-20 border-b border-white/5 flex items-center px-8 bg-panel/50 backdrop-blur-md sticky top-0 z-10">
          <h2 className="text-white font-semibold flex items-center gap-2"><Database className="text-primary" /> Evidence Management</h2>
        </header>

        <div className="p-8 max-w-5xl mx-auto w-full space-y-6">
          <div className="glass p-8 rounded-2xl border border-primary/20">
            <h3 className="text-xl font-bold text-white mb-6">Initialize Evidence Upload</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-mono">Target Operation / Case</label>
                <select 
                  className="w-full bg-panel border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary transition-colors appearance-none"
                  value={selectedCase}
                  onChange={e => setSelectedCase(e.target.value)}
                >
                  <option value="">-- Select Active Case --</option>
                  {cases.map(c => (
                    <option key={c.id} value={c.id}>#{c.id} - {c.title} [{c.risk_level}]</option>
                  ))}
                </select>
              </div>

              <div className="border-2 border-dashed border-white/10 rounded-xl p-10 flex flex-col items-center justify-center bg-panel/30 hover:bg-panel/50 hover:border-primary/50 transition-colors cursor-pointer relative">
                <input 
                  type="file" 
                  multiple 
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={handleFileChange}
                />
                <UploadCloud className="h-12 w-12 text-primary/50 mb-4" />
                <p className="text-white font-medium">Drag & Drop Intel Files</p>
                <p className="text-xs text-slate-500 mt-2 font-mono">Supported: PDF, JPG, PNG, CSV</p>
              </div>

              {files.length > 0 && (
                <div className="bg-panel rounded-lg p-4 border border-white/5">
                  <p className="text-sm text-slate-400 mb-2">Staged Files ({files.length}):</p>
                  <ul className="text-xs text-white space-y-1">
                    {files.map(f => <li key={f.name} className="flex items-center gap-2"><CheckCircle className="h-3 w-3 text-success" /> {f.name} ({(f.size / 1024).toFixed(1)} KB)</li>)}
                  </ul>
                </div>
              )}

              <button 
                onClick={handleUpload}
                disabled={!selectedCase || files.length === 0}
                className="w-full bg-primary hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg transition-colors flex justify-center items-center gap-2"
              >
                SECURE UPLOAD & EXTRACT
              </button>

              {status && (
                <div className={`p-4 rounded-lg flex items-center gap-3 text-sm font-medium ${status.includes('complete') ? 'bg-success/20 text-success' : 'bg-primary/20 text-primary'}`}>
                  {status.includes('complete') ? <CheckCircle className="h-5 w-5" /> : <AlertCircle className="h-5 w-5 animate-pulse" />}
                  {status}
                </div>
              )}
            </div>
          </div>

          {results.length > 0 && (
            <div className="glass p-8 rounded-2xl border border-accent/20">
              <h3 className="text-xl font-bold text-accent mb-6">Extraction Intelligence Report</h3>
              <div className="space-y-4">
                {results.map(res => (
                  <div key={res.id} className="bg-panel rounded-lg p-4 border border-white/5">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="font-bold text-white text-sm">{res.original_filename}</h4>
                      <span className="text-[10px] font-mono text-slate-500 bg-black px-2 py-1 rounded">SHA256: {res.sha256.substring(0, 16)}...</span>
                    </div>
                    
                    <div className="space-y-2">
                      <p className="text-[10px] uppercase text-slate-500 tracking-widest font-mono">Extracted Entities ({res.linked_entities?.length || 0})</p>
                      {res.linked_entities && res.linked_entities.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {res.linked_entities.map((ent: any) => (
                            <span key={ent.entity_id} className="bg-accent/10 text-accent border border-accent/20 px-2 py-1 rounded text-xs">
                              {ent.entity_type}: {ent.normalized_value}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No verifiable intelligence extracted from this file.</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
