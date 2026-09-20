import { useState } from 'react';
import { SlidersIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export type CandidateFilterValues = {
  target_role: string;
  source: string;
  skills: string[];
  min_experience?: number;
  max_experience?: number;
  is_shortlisted?: boolean;
};

type CandidateFiltersProps = {
  value: CandidateFilterValues;
  onApply: (value: CandidateFilterValues) => void;
  onClear: () => void;
  hasActiveFilters: boolean;
  disabled?: boolean;
};

const parseSkills = (text: string): string[] =>
  text
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);

export function CandidateFilters({
  value,
  onApply,
  onClear,
  hasActiveFilters,
  disabled,
}: CandidateFiltersProps) {
  const [targetRole, setTargetRole] = useState(value.target_role);
  const [source, setSource] = useState(value.source);
  const [skillsText, setSkillsText] = useState(value.skills.join(', '));
  const [minExperience, setMinExperience] = useState(
    value.min_experience === undefined ? '' : String(value.min_experience),
  );
  const [maxExperience, setMaxExperience] = useState(
    value.max_experience === undefined ? '' : String(value.max_experience),
  );
  const [shortlisted, setShortlisted] = useState<string>(
    value.is_shortlisted === undefined ? 'any' : value.is_shortlisted ? 'true' : 'false',
  );

  function handleApply() {
    onApply({
      target_role: targetRole.trim(),
      source: source.trim(),
      skills: parseSkills(skillsText),
      min_experience:
        minExperience === '' ? undefined : Math.max(0, Math.trunc(Number(minExperience))),
      max_experience:
        maxExperience === '' ? undefined : Math.max(0, Math.trunc(Number(maxExperience))),
      is_shortlisted: shortlisted === 'any' ? undefined : shortlisted === 'true',
    });
  }

  function handleClear() {
    setTargetRole('');
    setSource('');
    setSkillsText('');
    setMinExperience('');
    setMaxExperience('');
    setShortlisted('any');
    onClear();
  }

  return (
    <section
      aria-label="Filters"
      className="rounded-none border border-border bg-card p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <SlidersIcon className="size-4 text-primary" />
        <h2 className="text-xs font-semibold tracking-wide text-foreground uppercase">Filters</h2>
        {hasActiveFilters ? (
          <span className="rounded-none bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
            Active
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-3 md:grid-cols-4 lg:grid-cols-6">
        <div className="col-span-1">
          <Label htmlFor="filter-role" className="mb-1.5 block text-xs text-muted-foreground">
            Target role
          </Label>
          <Input
            id="filter-role"
            value={targetRole}
            onChange={(event) => setTargetRole(event.target.value)}
            placeholder="e.g. Backend Engineer"
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-source" className="mb-1.5 block text-xs text-muted-foreground">
            Source
          </Label>
          <Input
            id="filter-source"
            value={source}
            onChange={(event) => setSource(event.target.value)}
            placeholder="e.g. LinkedIn"
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-skills" className="mb-1.5 block text-xs text-muted-foreground">
            Skills
          </Label>
          <Input
            id="filter-skills"
            value={skillsText}
            onChange={(event) => setSkillsText(event.target.value)}
            placeholder="All of: Python, FastAPI"
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-min-exp" className="mb-1.5 block text-xs text-muted-foreground">
            Min experience
          </Label>
          <Input
            id="filter-min-exp"
            type="number"
            min={0}
            value={minExperience}
            onChange={(event) => setMinExperience(event.target.value)}
            placeholder="0"
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-max-exp" className="mb-1.5 block text-xs text-muted-foreground">
            Max experience
          </Label>
          <Input
            id="filter-max-exp"
            type="number"
            min={0}
            value={maxExperience}
            onChange={(event) => setMaxExperience(event.target.value)}
            placeholder="No limit"
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-shortlisted" className="mb-1.5 block text-xs text-muted-foreground">
            Shortlisted
          </Label>
          <Select
            value={shortlisted}
            onValueChange={(next) => setShortlisted(next)}
            disabled={disabled}
          >
            <SelectTrigger id="filter-shortlisted" className="w-full">
              <SelectValue placeholder="Any" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any</SelectItem>
              <SelectItem value="true">Shortlisted</SelectItem>
              <SelectItem value="false">Not shortlisted</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Button variant="default" size="sm" onClick={handleApply} disabled={disabled}>
          Apply filters
        </Button>
        <Button variant="outline" size="sm" onClick={handleClear} disabled={disabled}>
          Clear
        </Button>
      </div>
    </section>
  );
}