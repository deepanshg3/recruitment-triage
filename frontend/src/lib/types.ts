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
  sort_by?: CandidateSortField;
  sort_order?: SortOrder;
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