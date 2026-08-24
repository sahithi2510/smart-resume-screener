const API_BASE_URL = 'http://localhost:8000'

export interface UploadedResume {
  id: number
  source_filename: string
  message: string
}

export interface ScoredCandidate {
  resume_id: number
  source_filename?: string | null
  overall_score: number
  sub_scores: Record<string, number>
  matched_skills: string[]
  missing_skills: string[]
  justification: string
  confidence: number
  high_variance: boolean
  run_scores?: number[] | null
}

export interface ScoreResponse {
  scored_candidates: ScoredCandidate[]
  job_description: {
    required_skills?: string[]
    preferred_skills?: string[]
    min_years_experience?: number
    education_requirement?: string | null
    [key: string]: unknown
  }
}

export async function uploadResume(file: File): Promise<UploadedResume> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/resumes/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(
      error?.detail || `Upload failed (${response.status})`
    )
  }

  return response.json()
}

export async function scoreResumes(
  jobDescriptionText: string,
  topN: number
): Promise<ScoreResponse> {
  const response = await fetch(`${API_BASE_URL}/match/score`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_description_text: jobDescriptionText,
      top_n: topN,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(
      error?.detail || `Scoring failed (${response.status})`
    )
  }

  return response.json()
}

export async function checkBackend(): Promise<boolean> {
  try {
    const response = await fetch(API_BASE_URL)
    return response.ok
  } catch {
    return false
  }
}