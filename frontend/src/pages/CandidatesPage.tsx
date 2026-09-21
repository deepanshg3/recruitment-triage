import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  CaretLeftIcon,
  CaretRightIcon,
} from '@phosphor-icons/react';
import { CandidateDrawer } from '@/components/candidates/CandidateDrawer';
import {
  CandidateFilters,
  type CandidateFilterValues,
  type FilterOptions,
} from '@/components/candidates/CandidateFilters';
import { CandidateSearch } from '@/components/candidates/CandidateSearch';
import { CandidateTable } from '@/components/candidates/CandidateTable';
import { Header } from '@/components/layout/Header';
import {
  MatchDialog,
} from '@/components/matching/MatchDialog';
import { MatchResultsView } from '@/components/matching/MatchResultsView';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError, checkHealth, listCandidates, matchCandidates, updateShortlist } from '@/lib/api';
import type {
  ActiveSort,
  Candidate,
  CandidateListResponse,
  CandidateSortField,
  MatchResponse,
} from '@/lib/types';

const PAGE_SIZE = 20;
const OPTIONS_PAGE_SIZE = 100;

const EMPTY_FILTERS: CandidateFilterValues = {
  target_role: [],
  source: [],
  skills: [],
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return 'Something went wrong. Please try again.';
}

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  );
}

const EMPTY_OPTIONS: FilterOptions = { roles: [], sources: [], skills: [] };

export function CandidatesPage() {
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');

  const [filters, setFilters] = useState<CandidateFilterValues>(EMPTY_FILTERS);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>(EMPTY_OPTIONS);
  const [sorts, setSorts] = useState<ActiveSort[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(PAGE_SIZE);

  const [data, setData] = useState<CandidateListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [appReady, setAppReady] = useState(false);

  const [drawerCandidate, setDrawerCandidate] = useState<Candidate | null>(null);

  const [matchOpen, setMatchOpen] = useState(false);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [view, setView] = useState<'candidates' | 'match'>('candidates');

  useEffect(() => {
    // Wake the Render backend exactly once per page load, before the first
    // data requests. While the health request is in flight (Render may be
    // cold-starting the backend), the existing loading state stays on screen.
    // A health failure is not fatal here: the data requests below surface the
    // real error through the existing "Unable to load candidates" alert.
    void checkHealth()
      .catch(() => undefined)
      .finally(() => setAppReady(true));
  }, []);

  useEffect(() => {
    if (!appReady) return;
    let ignore = false;

    setLoading(true);
    setError(null);

    listCandidates({
      search: appliedSearch || undefined,
      target_role: filters.target_role.length > 0 ? filters.target_role : undefined,
      source: filters.source.length > 0 ? filters.source : undefined,
      skills: filters.skills.length > 0 ? filters.skills : undefined,
      min_experience: filters.min_experience,
      max_experience: filters.max_experience,
      is_shortlisted: filters.is_shortlisted,
      sorts: sorts.length > 0 ? sorts : undefined,
      page,
      page_size: pageSize,
    })
      .then((response) => {
        if (ignore) return;
        setData(response);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (ignore) return;
        setError(errorMessage(err));
        setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [appliedSearch, filters, sorts, page, pageSize, refreshKey, appReady]);

  useEffect(() => {
    if (!appReady) return;
    let ignore = false;

    listCandidates({ page_size: OPTIONS_PAGE_SIZE })
      .then((response) => {
        if (ignore) return;
        setFilterOptions({
          roles: uniqueSorted(response.items.map((candidate) => candidate.target_role)),
          sources: uniqueSorted(response.items.map((candidate) => candidate.source)),
          skills: uniqueSorted(response.items.flatMap((candidate) => candidate.skills)),
        });
      })
      .catch(() => {
        if (ignore) return;
        setFilterOptions(EMPTY_OPTIONS);
      });

    return () => {
      ignore = true;
    };
  }, [appReady]);

  const activeCount = useMemo(
    () =>
      (appliedSearch !== '' ? 1 : 0) +
      (filters.target_role.length > 0 ? 1 : 0) +
      (filters.source.length > 0 ? 1 : 0) +
      (filters.skills.length > 0 ? 1 : 0) +
      (filters.min_experience !== undefined || filters.max_experience !== undefined ? 1 : 0) +
      (filters.is_shortlisted !== undefined ? 1 : 0),
    [appliedSearch, filters],
  );

  const handleSearchChange = useCallback((value: string) => {
    setSearchText(value);
  }, []);

  const handleSearchSubmit = useCallback((value: string) => {
    setAppliedSearch(value);
    setPage(1);
  }, []);

  const handleSearchClear = useCallback(() => {
    setSearchText('');
    setAppliedSearch('');
    setPage(1);
  }, []);

  const handleChangeFilters = useCallback((next: CandidateFilterValues) => {
    setFilters(next);
    setPage(1);
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters(EMPTY_FILTERS);
    setSearchText('');
    setAppliedSearch('');
    setSorts([]);
    setPage(1);
  }, []);

  const handleSortChange = useCallback((field: CandidateSortField) => {
    setSorts((current) => {
      const index = current.findIndex((sort) => sort.field === field);
      if (index === -1) {
        return [...current, { field, direction: 'asc' }];
      }
      if (current[index].direction === 'asc') {
        const next = [...current];
        next[index] = { field, direction: 'desc' };
        return next;
      }
      return current.filter((sort) => sort.field !== field);
    });
    setPage(1);
  }, []);

  const handleRemoveSort = useCallback((field: CandidateSortField) => {
    setSorts((current) => current.filter((sort) => sort.field !== field));
    setPage(1);
  }, []);

  function patchCandidate(updated: Candidate) {
    setData((current) =>
      current
        ? { ...current, items: current.items.map((c) => (c.id === updated.id ? updated : c)) }
        : current,
    );
    setDrawerCandidate((current) => (current?.id === updated.id ? updated : current));
    setMatchResult((current) =>
      current
        ? {
            ...current,
            results: current.results.map((item) =>
              item.candidate.id === updated.id ? { ...item, candidate: updated } : item,
            ),
          }
        : current,
    );
  }

  const handleToggleShortlist = useCallback(async (candidate: Candidate) => {
    const nextValue = !candidate.is_shortlisted;

    setData((current) =>
      current
        ? {
            ...current,
            items: current.items.map((c) =>
              c.id === candidate.id ? { ...c, is_shortlisted: nextValue } : c,
            ),
          }
        : current,
    );
    setDrawerCandidate((current) =>
      current?.id === candidate.id ? { ...current, is_shortlisted: nextValue } : current,
    );
    setMatchResult((current) =>
      current
        ? {
            ...current,
            results: current.results.map((item) =>
              item.candidate.id === candidate.id
                ? { ...item, candidate: { ...item.candidate, is_shortlisted: nextValue } }
                : item,
            ),
          }
        : current,
    );

    try {
      const updated = await updateShortlist(candidate.id, nextValue);
      patchCandidate(updated);
      toast.success(
        nextValue ? `${candidate.name} added to shortlist` : `${candidate.name} removed from shortlist`,
      );
    } catch (err) {
      setData((current) =>
        current
          ? {
              ...current,
              items: current.items.map((c) =>
                c.id === candidate.id ? { ...c, is_shortlisted: candidate.is_shortlisted } : c,
              ),
            }
          : current,
      );
      setDrawerCandidate((current) =>
        current?.id === candidate.id ? { ...current, is_shortlisted: candidate.is_shortlisted } : current,
      );
      setMatchResult((current) =>
        current
          ? {
              ...current,
              results: current.results.map((item) =>
                item.candidate.id === candidate.id
                  ? { ...item, candidate: { ...item.candidate, is_shortlisted: candidate.is_shortlisted } }
                  : item,
              ),
            }
          : current,
      );
      toast.error(`Couldn't update shortlist: ${errorMessage(err)}`);
    }
  }, []);

  const handleSelectCandidate = useCallback((candidateId: string) => {
    const found =
      data?.items.find((c) => c.id === candidateId) ??
      matchResult?.results.find((r) => r.candidate.id === candidateId)?.candidate;
    if (found) setDrawerCandidate(found);
  }, [data, matchResult]);

  async function handleMatchSubmit(jobDescription: string, topK: number) {
    setMatchLoading(true);
    setMatchError(null);
    try {
      const response = await matchCandidates(jobDescription, topK);
      setMatchResult(response);
      setMatchOpen(false);
      setView('match');
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 503
          ? 'AI matching is currently unavailable. Please try again later.'
          : errorMessage(err);
      setMatchError(message);
    } finally {
      setMatchLoading(false);
    }
  }

  const handleBackToCandidates = useCallback(() => {
    setView('candidates');
  }, []);

  const handleClearMatch = useCallback(() => {
    setMatchResult(null);
    setView('candidates');
  }, []);

  const total = data?.total ?? 0;
  const fromItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const toItem = Math.min(page * pageSize, total);

  if (view === 'match' && matchResult) {
    return (
      <div className="min-h-dvh bg-background">
        <Header onOpenMatch={() => setMatchOpen(true)} />

        <main className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mt-6">
            <MatchResultsView
              result={matchResult}
              onBack={handleBackToCandidates}
              onClear={handleClearMatch}
              onToggleShortlist={handleToggleShortlist}
              onSelectCandidate={handleSelectCandidate}
            />
          </div>
        </main>

        <MatchDialog
          open={matchOpen}
          onOpenChange={setMatchOpen}
          onSubmit={handleMatchSubmit}
          loading={matchLoading}
          error={matchError}
        />

        <CandidateDrawer
          candidate={drawerCandidate}
          onOpenChange={(open) => {
            if (!open) setDrawerCandidate(null);
          }}
          onToggleShortlist={handleToggleShortlist}
        />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-background">
      <Header onOpenMatch={() => setMatchOpen(true)} />

      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mt-6 mb-4">
          <CandidateSearch
            value={searchText}
            onChange={handleSearchChange}
            onSubmit={handleSearchSubmit}
            onClear={handleSearchClear}
            disabled={loading}
          />
        </div>

        <CandidateFilters
          value={filters}
          options={filterOptions}
          onChange={handleChangeFilters}
          onClear={handleClearFilters}
          activeCount={activeCount}
          search={appliedSearch}
          onRemoveSearch={handleSearchClear}
          sorts={sorts}
          onRemoveSort={handleRemoveSort}
          disabled={loading}
        />

        <p className="mt-3 text-xs text-muted-foreground">
          {loading ? 'Loading candidates…' : `${total} candidate${total === 1 ? '' : 's'}`}
        </p>

        <div className="mt-2">
          {error ? (
            <Alert variant="destructive" className="mb-4">
              <AlertTitle>Unable to load candidates</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => setRefreshKey((key) => key + 1)}
              >
                Retry
              </Button>
            </Alert>
          ) : data && !loading ? (
            <CandidateTable
              candidates={data.items}
              sorts={sorts}
              onSortChange={handleSortChange}
              onSelectCandidate={(candidate) => setDrawerCandidate(candidate)}
              onToggleShortlist={handleToggleShortlist}
              disabled={false}
            />
          ) : (
            <div className="border border-border bg-card p-4">
              <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-10 w-full rounded-none" />
                ))}
              </div>
            </div>
          )}
        </div>

        {!error && !loading && data && total > 0 ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border border-t-0 border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">
              Showing {fromItem}–{toItem} of {total} candidate{total === 1 ? '' : 's'}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1 || loading}
              >
                <CaretLeftIcon className="size-3.5" />
                Previous
              </Button>
              <span className="text-xs text-muted-foreground tabular-nums">
                Page {page} of {Math.max(data.total_pages, 1)}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => current + 1)}
                disabled={page >= Math.max(data.total_pages, 1) || loading}
              >
                Next
                <CaretRightIcon className="size-3.5" />
              </Button>
            </div>
          </div>
        ) : null}
      </main>

      <MatchDialog
        open={matchOpen}
        onOpenChange={setMatchOpen}
        onSubmit={handleMatchSubmit}
        loading={matchLoading}
        error={matchError}
      />

      <CandidateDrawer
        candidate={drawerCandidate}
        onOpenChange={(open) => {
          if (!open) setDrawerCandidate(null);
        }}
        onToggleShortlist={handleToggleShortlist}
      />
    </div>
  );
}