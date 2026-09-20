import {
  CalendarBlankIcon,
  BriefcaseIcon,
  NotePencilIcon,
  StarIcon,
} from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { formatAppliedDate, formatYears } from '@/lib/format';
import type { Candidate } from '@/lib/types';

type CandidateDrawerProps = {
  candidate: Candidate | null;
  onOpenChange: (open: boolean) => void;
  onToggleShortlist: (candidate: Candidate) => void;
};

function DetailRow({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div className="min-w-0 flex-1">
        <dt className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
          {label}
        </dt>
        <dd className="mt-0.5 text-sm text-foreground">{children}</dd>
      </div>
    </div>
  );
}

export function CandidateDrawer({ candidate, onOpenChange, onToggleShortlist }: CandidateDrawerProps) {
  return (
    <Sheet open={candidate !== null} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-md">
        {candidate ? (
          <>
            <SheetHeader className="border-b border-border">
              <SheetTitle className="text-base">
                {candidate.name}
                {candidate.is_shortlisted ? (
                  <StarIcon weight="fill" className="ml-1.5 inline size-4 text-primary" />
                ) : null}
              </SheetTitle>
              <SheetDescription>{candidate.target_role}</SheetDescription>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto p-4">
              {candidate.notes ? (
                <div className="mb-4 border border-border bg-muted/60 p-3">
                  <p className="mb-1 flex items-center gap-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                    <NotePencilIcon className="size-3.5" />
                    Notes
                  </p>
                  <p className="text-sm leading-relaxed text-foreground">{candidate.notes}</p>
                </div>
              ) : null}

              {candidate.skills.length > 0 ? (
                <div className="mb-4">
                  <p className="mb-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                    Skills
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.skills.map((skill) => (
                      <Badge key={skill} variant="secondary">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}

              <Separator className="my-4" />

              <dl className="space-y-4">
                <DetailRow icon={<BriefcaseIcon className="size-4" />} label="Experience">
                  {formatYears(candidate.years_experience)}
                </DetailRow>
                <DetailRow icon={<CalendarBlankIcon className="size-4" />} label="Applied date">
                  {formatAppliedDate(candidate.applied_date)}
                </DetailRow>
                <DetailRow icon={<StarIcon className="size-4" />} label="Source">
                  {candidate.source}
                </DetailRow>
              </dl>
            </div>

            <SheetFooter className="border-t border-border">
              <Button
                variant={candidate.is_shortlisted ? 'outline' : 'default'}
                onClick={() => onToggleShortlist(candidate)}
                className="w-full"
                aria-pressed={candidate.is_shortlisted}
              >
                <StarIcon weight={candidate.is_shortlisted ? 'fill' : 'regular'} className="size-4" />
                {candidate.is_shortlisted ? 'Remove from shortlist' : 'Add to shortlist'}
              </Button>
            </SheetFooter>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}