export type Candidate = {
  id: string;
  name: string;
  target_role: string;
  years_experience: number;
  source: string;
  skills: string[];
  notes: string;
  applied_date: string;
  is_shortlisted: boolean;
};

export type CandidateListResponse = {
  items: Candidate[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type CandidateSortField =
  | 'name'
  | 'target_role'
  | 'years_experience'
  | 'applied_date';

export type SortOrder = 'asc' | 'desc';

/** One active sort; index in the array defines priority (0 = primary). */
export type ActiveSort = {
  field: CandidateSortField;
  direction: SortOrder;
};

export type CandidateListParams = {
  search?: string;
  /** Multiple values are OR-ed together within the category. */
  target_role?: string[];
  min_experience?: number;
  max_experience?: number;
  /** Multiple values are OR-ed together within the category. */
  source?: string[];
  /** ALL selected skills must be present on a candidate. */
  skills?: string[];
  is_shortlisted?: boolean;
  /** Ordered list of active sorts; index 0 is the primary sort. */
  sorts?: ActiveSort[];
  page?: number;
  page_size?: number;
};

export type CandidateUpdate = {
  is_shortlisted: boolean;
};

export type ScreeningReport = {
  candidate_id: string;
  candidate_name: string;
  strengths: string[];
  gaps: string[];
  evidence: string[];
  interview_questions: string[];
  overall_assessment: string | null;
};

export type MatchResultItem = {
  candidate: Candidate;
  retrieval_distance: number;
  screening: ScreeningReport | null;
  screening_error: string | null;
};

export type MatchResponse = {
  job_description: string;
  top_k_requested: number;
  results: MatchResultItem[];
};