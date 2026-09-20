import { CaretLeftIcon, InfoIcon, XIcon } from '@phosphor-icons/react';
import { ShortlistButton } from '@/components/candidates/ShortlistButton';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { formatSimilarity, formatYears } from '@/lib/format';
import type { Candidate, MatchResponse } from '@/lib/types';
import { ScreeningReport } from './ScreeningReport';

type MatchResultsViewProps = {
  result: MatchResponse;
  onBack: () => void;
  onClear: () => void;
  onToggleShortlist: (candidate: Candidate) => void;
  onSelectCandidate: (candidateId: string) => void;
};

type MatchResultCardProps = {
  item: MatchResponse['results'][number];
  expandedByDefault: boolean;
  onToggleShortlist: (candidate: Candidate) => void;
  onSelectCandidate: (candidateId: string) => void;
};

function MatchResultCard({
  item,
  expandedByDefault,
  onToggleShortlist,
  onSelectCandidate,
}: MatchResultCardProps) {
  return (
    <article className="border border-border bg-card">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <ShortlistButton candidate={item.candidate} onToggle={onToggleShortlist} />
          <button
            type="button"
            onClick={() => onSelectCandidate(item.candidate.id)}
            className="min-w-0 truncate text-left text-sm font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
          >
            {item.candidate.name}
          </button>
          <Badge variant="secondary" className="hidden min-w-0 truncate sm:inline-flex">
            {item.candidate.target_role} · {formatYears(item.candidate.years_experience)}
          </Badge>
        </div>
        <div className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
          <span className="sr-only">Similarity</span>
          <span>Similarity</span>
          <span className="font-medium text-foreground tabular-nums">
            {formatSimilarity(item.retrieval_distance)}
          </span>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                tabIndex={0}
                className="cursor-help text-muted-foreground/70 outline-none focus-visible:ring-1 focus-visible:ring-ring/50 hover:text-muted-foreground"
                aria-label="About similarity"
              >
                <InfoIcon className="size-3.5" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              Similarity indicates how closely the candidate's profile matches the job description
              based on semantic retrieval. It is not a hiring probability.
            </TooltipContent>
          </Tooltip>
        </div>
      </header>

      <Separator />

      <div className="px-4 py-3">
        {item.screening ? (
          <Accordion
            type="single"
            collapsible
            defaultValue={expandedByDefault ? `screening-${item.candidate.id}` : undefined}
          >
            <AccordionItem value={`screening-${item.candidate.id}`} className="border-0">
              <AccordionTrigger className="text-xs font-medium text-primary hover:no-underline">
                Screening report
              </AccordionTrigger>
              <AccordionContent className="pt-3 pb-0">
                <ScreeningReport report={item.screening} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        ) : null}

        {item.screening_error ? (
          <Alert variant="destructive">
            <AlertTitle>Screen report unavailable</AlertTitle>
            <AlertDescription>{item.screening_error}</AlertDescription>
          </Alert>
        ) : null}

        {!item.screening && !item.screening_error ? (
          <p className="text-xs text-muted-foreground">Candidate retrieved but not screened.</p>
        ) : null}
      </div>
    </article>
  );
}

export function MatchResultsView({
  result,
  onBack,
  onClear,
  onToggleShortlist,
  onSelectCandidate,
}: MatchResultsViewProps) {
  const { results } = result;

  return (
    <div className="pb-12">
      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <CaretLeftIcon className="size-3.5" />
          Back to candidates
        </Button>
        <Button variant="ghost" size="sm" onClick={onClear} aria-label="Clear AI match results">
          <XIcon className="size-3.5" />
          Clear results
        </Button>
      </div>

      <h2 className="mt-3 text-lg font-semibold tracking-tight text-foreground">
        AI Match results
      </h2>

      <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground line-clamp-2">
        {result.job_description}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {results.length} candidate{results.length === 1 ? '' : 's'} screened · top{' '}
        {result.top_k_requested}
      </p>

      {results.length === 0 ? (
        <div className="mt-4 border border-border bg-card p-12 text-center" aria-live="polite">
          <p className="text-sm text-muted-foreground">No matching results yet.</p>
        </div>
      ) : (
        <div className="mt-4 space-y-3" aria-live="polite">
          {results.map((item, index) => (
            <MatchResultCard
              key={item.candidate.id}
              item={item}
              expandedByDefault={index === 0}
              onToggleShortlist={onToggleShortlist}
              onSelectCandidate={onSelectCandidate}
            />
          ))}
        </div>
      )}
    </div>
  );
}