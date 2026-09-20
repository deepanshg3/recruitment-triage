import { StarIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { Candidate } from '@/lib/types';

type ShortlistButtonProps = {
  candidate: Candidate;
  onToggle: (candidate: Candidate) => void;
  disabled?: boolean;
};

export function ShortlistButton({ candidate, onToggle, disabled }: ShortlistButtonProps) {
  const isShortlisted = candidate.is_shortlisted;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant={isShortlisted ? 'ghost' : 'ghost'}
          size="icon-sm"
          onClick={() => onToggle(candidate)}
          disabled={disabled}
          aria-label={isShortlisted ? 'Remove from shortlist' : 'Add to shortlist'}
          aria-pressed={isShortlisted}
          className={isShortlisted ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}
          data-state={isShortlisted ? 'shortlisted' : undefined}
        >
          <StarIcon
            className="size-4"
            weight={isShortlisted ? 'fill' : 'regular'}
          />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top">
        {isShortlisted ? 'Remove from shortlist' : 'Add to shortlist'}
      </TooltipContent>
    </Tooltip>
  );
}