import { useState, useEffect } from 'react'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'

interface ApiStatus {
  status: 'checking' | 'connected' | 'disconnected';
  version?: string;
  error?: string;
}

const mockAnalyticsData = [
  { month: 'Jan', processed: 45, matched: 12 },
  { month: 'Feb', processed: 80, matched: 28 },
  { month: 'Mar', processed: 120, matched: 45 },
  { month: 'Apr', processed: 160, matched: 70 },
  { month: 'May', processed: 220, matched: 110 },
  { month: 'Jun', processed: 310, matched: 180 },
]

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>({ status: 'checking' })

  useEffect(() => {
    const checkApi = async () => {
      try {
        const response = await fetch('http://localhost:8000/')
        if (response.ok) {
          const data = await response.json()
          setApiStatus({
            status: 'connected',
            version: data.version || '0.1.0'
          })
        } else {
          setApiStatus({ status: 'disconnected', error: 'HTTP error status' })
        }
      } catch (err) {
        setApiStatus({ status: 'disconnected', error: 'Backend is not running. Start it with docker compose up --build.' })
      }
    }
    
    // Check immediately and poll every 5 seconds
    checkApi()
    const interval = setInterval(checkApi, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Smart Resume Screener
              </h1>
              <p className="text-xs text-slate-500 font-medium">Scaffolding Verification Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="flex items-center gap-2 text-sm bg-slate-900 border border-slate-800 rounded-full px-4 py-1.5 font-medium">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Frontend (Vite + React)
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-6 md:p-8 space-y-8">
        
        {/* Banner Section */}
        <section className="relative rounded-3xl overflow-hidden bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 border border-slate-900 p-8 md:p-10">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(124,58,237,0.08),transparent_50%)]"></div>
          <div className="relative z-10 max-w-3xl space-y-4">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
              Scaffolding Installed Successfully
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white leading-tight">
              A Modern, Intelligent Engine for AI Resume Analysis
            </h2>
            <p className="text-slate-400 leading-relaxed text-base md:text-lg">
              This scaffold comprises a FastAPI backend using Python 3.12, PostgreSQL + pgvector databases for vector embeddings, and a React frontend bundled with Vite, Tailwind CSS, and Recharts.
            </p>
          </div>
        </section>

        {/* Scaffold Component Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* FastAPI backend status */}
          <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 flex flex-col justify-between hover:border-slate-800 transition duration-300">
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-sky-400">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                  </svg>
                </div>
                {apiStatus.status === 'connected' ? (
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Online
                  </span>
                ) : apiStatus.status === 'checking' ? (
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                    Connecting...
                  </span>
                ) : (
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    Offline
                  </span>
                )}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">FastAPI Backend</h3>
                <p className="text-sm text-slate-400 mt-1">Uvicorn dev-server auto-reload</p>
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800/60 text-xs">
              {apiStatus.status === 'connected' ? (
                <div className="flex justify-between text-slate-400">
                  <span>API version:</span>
                  <span className="font-mono text-emerald-400 font-bold">{apiStatus.version}</span>
                </div>
              ) : (
                <p className="text-slate-500 italic text-xs leading-normal">
                  {apiStatus.error || "Launch backend using docker compose."}
                </p>
              )}
            </div>
          </div>

          {/* Database status */}
          <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 flex flex-col justify-between hover:border-slate-800 transition duration-300">
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-indigo-400">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path>
                  </svg>
                </div>
                {apiStatus.status === 'connected' ? (
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Online
                  </span>
                ) : (
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-slate-800 text-slate-500 border border-slate-800">
                    Waiting...
                  </span>
                )}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">PostgreSQL + pgvector</h3>
                <p className="text-sm text-slate-400 mt-1">Vector DB extension configured</p>
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800/60 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Database:</span>
                <span className="font-mono font-bold text-indigo-400">pgvector/pgvector:pg16</span>
              </div>
            </div>
          </div>

          {/* AI Embeddings Status */}
          <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 flex flex-col justify-between hover:border-slate-800 transition duration-300">
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-violet-400">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                  </svg>
                </div>
                <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
                  Ready
                </span>
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Sentence Transformers</h3>
                <p className="text-sm text-slate-400 mt-1">NLP library configured in backend</p>
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800/60 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Model Backend:</span>
                <span className="font-mono text-violet-400 font-bold">all-MiniLM-L6-v2</span>
              </div>
            </div>
          </div>
        </section>

        {/* Analytics Mock Visualization Section */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Chart */}
          <div className="lg:col-span-2 bg-slate-900/30 border border-slate-900 rounded-2xl p-6">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">Analytics Integration Preview</h3>
                <p className="text-xs text-slate-400">Visualizing mockup pipeline data using Recharts</p>
              </div>
              <span className="text-xs font-medium bg-slate-900 px-3 py-1 rounded-lg border border-slate-800 text-slate-300">
                Monthly Breakdown
              </span>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockAnalyticsData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorProcessed" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorMatched" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#0f172a', 
                      borderColor: '#1e293b',
                      borderRadius: '12px',
                      color: '#f8fafc'
                    }} 
                  />
                  <Area type="monotone" dataKey="processed" name="Resumes Processed" stroke="#4f46e5" strokeWidth={2} fillOpacity={1} fill="url(#colorProcessed)" />
                  <Area type="monotone" dataKey="matched" name="High Matches" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorMatched)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Quick Info & Action Panel */}
          <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-6 flex flex-col justify-between">
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white">Placeholder Upload Scaffolding</h3>
              <p className="text-xs text-slate-400">
                Interactive mockup area for the future resume parser utility.
              </p>

              {/* Mock upload zone */}
              <div className="border border-dashed border-slate-800 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:border-indigo-500/50 hover:bg-indigo-950/5 transition cursor-pointer group">
                <svg className="w-10 h-10 text-slate-500 group-hover:text-indigo-400 transition mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
                <span className="text-sm font-semibold text-slate-300">Upload PDF / DOCX</span>
                <span className="text-xs text-slate-500 mt-1">Select resumes to test upload</span>
              </div>
            </div>

            <div className="space-y-3 mt-6 pt-4 border-t border-slate-800/60">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">FastAPI Endpoints Configured</h4>
              <div className="grid grid-cols-1 gap-2 text-xs font-mono">
                <div className="flex items-center justify-between bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800/80">
                  <span className="text-emerald-400 font-bold">GET</span>
                  <span className="text-slate-300 font-semibold">/</span>
                </div>
                <div className="flex items-center justify-between bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800/80">
                  <span className="text-emerald-400 font-bold">GET</span>
                  <span className="text-slate-300 font-semibold">/docs</span>
                </div>
              </div>
            </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-6 text-center text-xs text-slate-500">
        <p>© 2026 Smart Resume Screener. Created by Google Antigravity.</p>
      </footer>
    </div>
  )
}

export default App
