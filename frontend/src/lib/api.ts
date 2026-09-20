import type {
  Candidate,
  CandidateListParams,
  CandidateListResponse,
  CandidateSortField,
  CandidateUpdate,
  MatchResponse,
  SortOrder,
} from './types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/+$/, '');

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
      ...init,
    });
  } catch {
    throw new ApiError(0, 'Unable to reach the server. Make sure the backend is running.');
  }

  const payload: unknown = await res.json().catch(() => null);

  if (!res.ok) {
    const detail = isRecord(payload) ? payload.detail : undefined;
    let message = `Request failed (${res.status})`;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail
        .map((item) => (isRecord(item) && typeof item.msg === 'string' ? item.msg : String(item)))
        .join(', ');
    }
    throw new ApiError(res.status, message);
  }

  return payload as T;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function listCandidates(params: CandidateListParams): Promise<CandidateListResponse> {
  const search = new URLSearchParams();
  const set = (key: string, value: string | number | undefined | null) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  };

  set('search', params.search);
  set('target_role', params.target_role);
  set('min_experience', params.min_experience);
  set('max_experience', params.max_experience);
  set('source', params.source);
  if (params.skills && params.skills.length > 0) {
    set('skills', params.skills.join(','));
  }
  if (params.is_shortlisted !== undefined) {
    set('is_shortlisted', params.is_shortlisted ? 'true' : 'false');
  }
  set('sort_by', params.sort_by as unknown as string);
  set('sort_order', params.sort_order as unknown as string);
  set('page', params.page);
  set('page_size', params.page_size);

  const query = search.toString();
  return request<CandidateListResponse>(`/candidates${query ? `?${query}` : ''}`);
}

export function getCandidate(id: string): Promise<Candidate> {
  return request<Candidate>(`/candidates/${id}`);
}

export function updateShortlist(id: string, isShortlisted: boolean): Promise<Candidate> {
  const body: CandidateUpdate = { is_shortlisted: isShortlisted };
  return request<Candidate>(`/candidates/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function matchCandidates(jobDescription: string, topK: number): Promise<MatchResponse> {
  return request<MatchResponse>('/match', {
    method: 'POST',
    body: JSON.stringify({ job_description: jobDescription, top_k: topK }),
  });
}

export type { CandidateSortField, SortOrder };