import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { StarIcon } from '@phosphor-icons/react';
import { formatDistance, formatYears } from '@/lib/format';
import type { MatchResponse } from '@/lib/types';
import { ScreeningReport } from './ScreeningReport';

type MatchResultsProps = {
  result: MatchResponse;
  onSelectCandidate: (candidateId: string) => void;
};

export function MatchResults({ result, onSelectCandidate }: MatchResultsProps) {
  const { results } = result;

  if (results.length === 0) {
    return (
      <div className="border border-border bg-card p-12 text-center" aria-live="polite">
        <p className="text-sm text-muted-foreground">No matching results yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3" aria-live="polite">
      {results.map((item) => (
        <article
          key={item.candidate.id}
          className="border border-border bg-card"
        >
          <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <button
                type="button"
                onClick={() => onSelectCandidate(item.candidate.id)}
                className="min-w-0 truncate text-left text-sm font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
              >
                {item.candidate.name}
              </button>
              {item.candidate.is_shortlisted ? (
                <StarIcon weight="fill" className="size-4 shrink-0 text-primary" />
              ) : null}
              <Badge variant="secondary" className="hidden shrink-0 sm:inline-flex">
                {item.candidate.target_role} · {formatYears(item.candidate.years_experience)}
              </Badge>
            </div>
            <div className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
              <span className="sr-only">Semantic distance</span>
              <span>Semantic distance</span>
              <span className="font-medium text-foreground tabular-nums">
                {formatDistance(item.retrieval_distance)}
              </span>
            </div>
          </header>

          <Separator />

          <div className="px-4 py-3">
            {item.screening ? (
              <Accordion type="single" collapsible>
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
      ))}
    </div>
  );
}