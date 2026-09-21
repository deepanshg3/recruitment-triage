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

let healthCheckPromise: Promise<void> | null = null;

/**
 * Wake the backend exactly once per full page load.
 *
 * Render cold-starts free-tier services on the first incoming request, so the
 * heavyweight data requests below can hit a sleeping API. GET /health is cheap
 * and is exactly what wakes it, so the app awaits this before the initial
 * candidates/options loads. The module-level promise guarantees a single
 * request per page load even if React StrictMode remounts components in dev —
 * every mount just reuses the same in-flight promise.
 */
export function checkHealth(): Promise<void> {
  if (healthCheckPromise === null) {
    healthCheckPromise = request<{ status: string }>('/health').then(() => undefined);
  }
  return healthCheckPromise;
}

export function listCandidates(params: CandidateListParams): Promise<CandidateListResponse> {
  const search = new URLSearchParams();
  const set = (key: string, value: string | number | undefined | null) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  };

  set('search', params.search);
  set('min_experience', params.min_experience);
  set('max_experience', params.max_experience);
  if (params.target_role && params.target_role.length > 0) {
    set('target_role', params.target_role.join(','));
  }
  if (params.source && params.source.length > 0) {
    set('source', params.source.join(','));
  }
  if (params.skills && params.skills.length > 0) {
    set('skills', params.skills.join(','));
  }
  if (params.is_shortlisted !== undefined) {
    set('is_shortlisted', params.is_shortlisted ? 'true' : 'false');
  }
  if (params.sorts && params.sorts.length > 0) {
    set('sort_by', params.sorts.map((sort) => sort.field).join(','));
    set('sort_order', params.sorts.map((sort) => sort.direction).join(','));
  }
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