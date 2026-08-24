import { useEffect, useState } from 'react'
import {
  uploadResume,
  scoreResumes,
  checkBackend,
  type ScoredCandidate,
  type ScoreResponse,
} from './services/api'

function App() {
  const [backendOnline, setBackendOnline] = useState(false)

  const [files, setFiles] = useState<File[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)

  const [jobDescription, setJobDescription] = useState('')
  const [topN, setTopN] = useState(5)

  const [results, setResults] = useState<ScoredCandidate[]>([])
  const [jobData, setJobData] = useState<ScoreResponse['job_description'] | null>(null)

  const [scoring, setScoring] = useState(false)
  const [error, setError] = useState('')
  const [selectedCandidate, setSelectedCandidate] =
    useState<ScoredCandidate | null>(null)

  useEffect(() => {
    const check = async () => {
      setBackendOnline(await checkBackend())
    }

    check()

    const interval = setInterval(check, 5000)

    return () => clearInterval(interval)
  }, [])

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!event.target.files) return

    const selected = Array.from(event.target.files)

    const validFiles = selected.filter((file) => {
      const name = file.name.toLowerCase()
      return name.endsWith('.pdf') || name.endsWith('.docx')
    })

    setFiles(validFiles)
    setError('')
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one PDF or DOCX resume.')
      return
    }

    setUploading(true)
    setError('')

    try {
      const uploadedNames: string[] = []

      for (const file of files) {
        const result = await uploadResume(file)
        uploadedNames.push(result.source_filename)
      }

      setUploadedFiles((previous) => [
        ...previous,
        ...uploadedNames,
      ])

      setFiles([])
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to upload resume.'
      )
    } finally {
      setUploading(false)
    }
  }

  const handleAnalyze = async () => {
    if (!jobDescription.trim()) {
      setError('Please enter a job description.')
      return
    }

    setScoring(true)
    setError('')
    setResults([])
    setSelectedCandidate(null)

    try {
      const response = await scoreResumes(
        jobDescription,
        topN
      )

      setResults(response.scored_candidates)
      setJobData(response.job_description)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to analyze candidates.'
      )
    } finally {
      setScoring(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">

      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/90 sticky top-0 z-50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">

          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center">
              <span className="text-xl">📄</span>
            </div>

            <div>
              <h1 className="text-xl font-bold">
                Smart Resume Screener
              </h1>

              <p className="text-xs text-slate-500">
                AI-powered candidate matching
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900 border border-slate-800 text-sm">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                backendOnline
                  ? 'bg-emerald-500 animate-pulse'
                  : 'bg-red-500'
              }`}
            />

            {backendOnline
              ? 'Backend Connected'
              : 'Backend Offline'}
          </div>

        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">

        {/* Hero */}
        <section className="rounded-3xl border border-slate-800 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 p-8">

          <span className="inline-block px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs font-semibold mb-4">
            AI Resume Screening
          </span>

          <h2 className="text-4xl font-extrabold mb-4">
            Find the best candidates faster.
          </h2>

          <p className="text-slate-400 max-w-3xl leading-relaxed">
            Upload resumes, provide a job description, and let the
            AI-powered matching pipeline rank candidates based on
            skills, experience, education and domain relevance.
          </p>

        </section>

        {/* Upload + JD */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Upload */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">

            <h3 className="text-lg font-bold mb-2">
              1. Upload Resumes
            </h3>

            <p className="text-sm text-slate-400 mb-5">
              Upload PDF or DOCX resumes for analysis.
            </p>

            <label className="block border-2 border-dashed border-slate-700 rounded-xl p-8 text-center cursor-pointer hover:border-violet-500 transition">

              <div className="text-4xl mb-3">
                📤
              </div>

              <p className="font-semibold">
                Choose Resume Files
              </p>

              <p className="text-xs text-slate-500 mt-1">
                PDF or DOCX
              </p>

              <input
                type="file"
                accept=".pdf,.docx"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />

            </label>

            {files.length > 0 && (
              <div className="mt-4 space-y-2">

                {files.map((file) => (
                  <div
                    key={file.name}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-sm flex justify-between"
                  >
                    <span>{file.name}</span>

                    <span className="text-slate-500">
                      {(file.size / 1024).toFixed(0)} KB
                    </span>
                  </div>
                ))}

                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="w-full mt-3 bg-violet-600 hover:bg-violet-500 disabled:bg-slate-700 py-3 rounded-xl font-semibold transition"
                >
                  {uploading
                    ? 'Uploading...'
                    : 'Upload Resumes'}
                </button>

              </div>
            )}

            {uploadedFiles.length > 0 && (
              <div className="mt-5">

                <p className="text-xs uppercase tracking-wider text-slate-500 font-bold mb-2">
                  Uploaded
                </p>

                <div className="space-y-2">

                  {uploadedFiles.map((name, index) => (
                    <div
                      key={`${name}-${index}`}
                      className="flex items-center gap-2 text-sm text-emerald-400"
                    >
                      ✓ {name}
                    </div>
                  ))}

                </div>

              </div>
            )}

          </div>

          {/* Job Description */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">

            <h3 className="text-lg font-bold mb-2">
              2. Job Description
            </h3>

            <p className="text-sm text-slate-400 mb-5">
              Paste the job description you want to screen candidates against.
            </p>

            <textarea
              value={jobDescription}
              onChange={(event) =>
                setJobDescription(event.target.value)
              }
              placeholder="Example: We are looking for a Software Engineer with Java, Spring Boot, SQL, PostgreSQL, REST API and Git experience..."
              className="w-full h-52 bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-violet-500 resize-none"
            />

            <div className="flex items-center justify-between mt-4">

              <label className="text-sm text-slate-400">
                Candidates to score:
              </label>

              <select
                value={topN}
                onChange={(event) =>
                  setTopN(Number(event.target.value))
                }
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2"
              >
                <option value={1}>1</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>

            </div>

          </div>

        </section>

        {/* Error */}
        {error && (
          <div className="bg-red-950/30 border border-red-900 rounded-xl p-4 text-red-400 text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Analyze */}
        <section className="flex justify-center">

          <button
            onClick={handleAnalyze}
            disabled={scoring || !backendOnline}
            className="px-10 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:from-slate-700 disabled:to-slate-700 font-bold text-lg shadow-lg shadow-violet-900/20 transition"
          >
            {scoring
              ? 'Analyzing Candidates...'
              : 'Analyze Candidates'}
          </button>

        </section>

        {/* Job extraction */}
        {jobData && (
          <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">

            <h3 className="text-lg font-bold mb-4">
              Extracted Job Requirements
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              <div>
                <p className="text-xs uppercase text-slate-500 font-bold mb-2">
                  Required Skills
                </p>

                <div className="flex flex-wrap gap-2">
                  {jobData.required_skills?.map((skill) => (
                    <span
                      key={skill}
                      className="px-3 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-xs"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase text-slate-500 font-bold mb-2">
                  Preferred Skills
                </p>

                <div className="flex flex-wrap gap-2">
                  {jobData.preferred_skills?.map((skill) => (
                    <span
                      key={skill}
                      className="px-3 py-1 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 text-xs"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

            </div>

          </section>
        )}

        {/* Results */}
        {results.length > 0 && (
          <section>

            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-2xl font-bold">
                  Candidate Rankings
                </h3>

                <p className="text-sm text-slate-500">
                  Ranked by AI match score
                </p>
              </div>

              <span className="px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-sm">
                {results.length} candidates
              </span>
            </div>

            <div className="space-y-4">

              {results.map((candidate, index) => (
                <div
                  key={candidate.resume_id}
                  className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 hover:border-slate-700 transition"
                >

                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">

                    <div className="flex items-center gap-4">

                      <div className="w-12 h-12 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center font-bold text-lg">
                        #{index + 1}
                      </div>

                      <div>
                        <h4 className="font-bold">
                          {candidate.source_filename ||
                            `Resume ${candidate.resume_id}`}
                        </h4>

                        <p className="text-xs text-slate-500">
                          Resume ID: {candidate.resume_id}
                        </p>
                      </div>

                    </div>

                    <div className="flex items-center gap-5">

                      <div className="text-right">
                        <p className="text-3xl font-extrabold text-violet-400">
                          {candidate.overall_score.toFixed(2)}
                        </p>

                        <p className="text-xs text-slate-500">
                          / 10
                        </p>
                      </div>

                      <div className="text-right">
                        <p className="font-semibold">
                          {(candidate.confidence * 100).toFixed(0)}%
                        </p>

                        <p className="text-xs text-slate-500">
                          Confidence
                        </p>
                      </div>

                      <button
                        onClick={() =>
                          setSelectedCandidate(
                            selectedCandidate?.resume_id ===
                              candidate.resume_id
                              ? null
                              : candidate
                          )
                        }
                        className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-semibold"
                      >
                        {selectedCandidate?.resume_id ===
                        candidate.resume_id
                          ? 'Hide'
                          : 'Details'}
                      </button>

                    </div>

                  </div>

                  {candidate.high_variance && (
                    <div className="mt-4 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
                      ⚠ Human review recommended — scoring runs showed high variance.
                    </div>
                  )}

                  {selectedCandidate?.resume_id ===
                    candidate.resume_id && (
                    <div className="mt-6 pt-6 border-t border-slate-800 space-y-6">

                      {/* Subscores */}
                      <div>

                        <h5 className="font-bold mb-3">
                          Score Breakdown
                        </h5>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

                          {Object.entries(
                            candidate.sub_scores
                          ).map(([key, value]) => (
                            <div
                              key={key}
                              className="bg-slate-950 rounded-xl p-4 border border-slate-800"
                            >
                              <p className="text-xs text-slate-500 capitalize">
                                {key.replaceAll('_', ' ')}
                              </p>

                              <p className="text-xl font-bold mt-1">
                                {value.toFixed(1)}
                              </p>

                            </div>
                          ))}

                        </div>

                      </div>

                      {/* Matched */}
                      <div>

                        <h5 className="font-bold mb-3">
                          Matched Skills
                        </h5>

                        <div className="flex flex-wrap gap-2">

                          {candidate.matched_skills.length > 0
                            ? candidate.matched_skills.map(
                                (skill) => (
                                  <span
                                    key={skill}
                                    className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs"
                                  >
                                    ✓ {skill}
                                  </span>
                                )
                              )
                            : (
                              <span className="text-sm text-slate-500">
                                No matching skills found.
                              </span>
                            )}

                        </div>

                      </div>

                      {/* Missing */}
                      <div>

                        <h5 className="font-bold mb-3">
                          Missing Required Skills
                        </h5>

                        <div className="flex flex-wrap gap-2">

                          {candidate.missing_skills.length > 0
                            ? candidate.missing_skills.map(
                                (skill) => (
                                  <span
                                    key={skill}
                                    className="px-3 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-xs"
                                  >
                                    ⚠ {skill}
                                  </span>
                                )
                              )
                            : (
                              <span className="text-sm text-emerald-400">
                                No required skills missing.
                              </span>
                            )}

                        </div>

                      </div>

                      {/* Justification */}
                      <div>

                        <h5 className="font-bold mb-2">
                          AI Justification
                        </h5>

                        <p className="text-sm text-slate-400 leading-relaxed">
                          {candidate.justification}
                        </p>

                      </div>

                      {/* Run scores */}
                      {candidate.run_scores &&
                        candidate.run_scores.length > 0 && (
                          <div>

                            <h5 className="font-bold mb-2">
                              Scoring Runs
                            </h5>

                            <div className="flex gap-3">

                              {candidate.run_scores.map(
                                (score, i) => (
                                  <span
                                    key={i}
                                    className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm"
                                  >
                                    Run {i + 1}:{' '}
                                    <strong>
                                      {score.toFixed(2)}
                                    </strong>
                                  </span>
                                )
                              )}

                            </div>

                          </div>
                        )}

                    </div>
                  )}

                </div>
              ))}

            </div>

          </section>
        )}

      </main>

      <footer className="border-t border-slate-900 mt-10 py-6 text-center text-xs text-slate-600">
        Smart Resume Screener • FastAPI + PostgreSQL + pgvector + AI
      </footer>

    </div>
  )
}

export default App