import { useEffect, useState } from 'react';
import { SlidersIcon, XIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { MultiSelect } from './MultiSelect';

export type CandidateFilterValues = {
  target_role: string[];
  source: string[];
  skills: string[];
  min_experience?: number;
  max_experience?: number;
  is_shortlisted?: boolean;
};

export type FilterOptions = {
  roles: string[];
  sources: string[];
  skills: string[];
};

type CandidateFiltersProps = {
  value: CandidateFilterValues;
  options: FilterOptions;
  onChange: (updated: CandidateFilterValues) => void;
  onClear: () => void;
  activeCount: number;
  /** Applied search query; rendered as a removable chip in the filter area. */
  search?: string;
  onRemoveSearch: () => void;
  disabled?: boolean;
};

function parseExperience(raw: string): number | undefined {
  if (raw.trim() === '') return undefined;
  const value = Math.trunc(Number(raw));
  return Number.isFinite(value) && value >= 0 ? value : undefined;
}

function CommitInput({
  id,
  label,
  placeholder,
  rawValue,
  disabled,
  onCommit,
}: {
  id: string;
  label: string;
  placeholder: string;
  rawValue: string;
  disabled?: boolean;
  onCommit: (value: number | undefined) => void;
}) {
  const [draft, setDraft] = useState(rawValue);

  useEffect(() => {
    setDraft(rawValue);
  }, [rawValue]);

  function commit() {
    onCommit(parseExperience(draft));
  }

  return (
    <div>
      <Label htmlFor={id} className="mb-1.5 block text-xs text-muted-foreground">
        {label}
      </Label>
      <Input
        id={id}
        type="number"
        min={0}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.currentTarget.blur();
          }
        }}
        placeholder={placeholder}
        disabled={disabled}
      />
    </div>
  );
}

export function CandidateFilters({
  value,
  options,
  onChange,
  onClear,
  activeCount,
  search,
  onRemoveSearch,
  disabled,
}: CandidateFiltersProps) {
  const shortlisted: 'any' | 'true' | 'false' =
    value.is_shortlisted === undefined ? 'any' : value.is_shortlisted ? 'true' : 'false';

  function update(partial: Partial<CandidateFilterValues>) {
    onChange({ ...value, ...partial });
  }

  function removeRole(role: string) {
    update({ target_role: value.target_role.filter((v) => v !== role) });
  }

  function removeSource(source: string) {
    update({ source: value.source.filter((v) => v !== source) });
  }

  function removeSkill(skill: string) {
    update({ skills: value.skills.filter((v) => v !== skill) });
  }

  function removeShortlist() {
    update({ is_shortlisted: undefined });
  }

  function removeExperience() {
    update({ min_experience: undefined, max_experience: undefined });
  }

  const chips: { key: string; label: string; onRemove: () => void }[] = [
    ...(search
      ? [{ key: 'search', label: `Search: ${search}`, onRemove: onRemoveSearch }]
      : []),
    ...value.target_role.map((role) => ({ key: `role-${role}`, label: role, onRemove: () => removeRole(role) })),
    ...value.source.map((source) => ({ key: `source-${source}`, label: source, onRemove: () => removeSource(source) })),
    ...value.skills.map((skill) => ({ key: `skill-${skill}`, label: skill, onRemove: () => removeSkill(skill) })),
    ...(value.is_shortlisted !== undefined
      ? [{
          key: 'shortlisted',
          label: value.is_shortlisted ? 'Shortlisted' : 'Not shortlisted',
          onRemove: removeShortlist,
        }]
      : []),
    ...(value.min_experience !== undefined || value.max_experience !== undefined
      ? [{
          key: 'experience',
          label: experienceLabel(value.min_experience, value.max_experience),
          onRemove: removeExperience,
        }]
      : []),
  ];

  return (
    <section aria-label="Filters" className="rounded-none border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <SlidersIcon className="size-4 text-primary" />
        <h2 className="text-xs font-semibold tracking-wide text-foreground uppercase">Filters</h2>
        {activeCount > 0 ? (
          <span className="rounded-none bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
            {activeCount} active
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-3 md:grid-cols-4 lg:grid-cols-6">
        <div className="col-span-1">
          <Label htmlFor="filter-role" className="mb-1.5 block text-xs text-muted-foreground">
            Target role
          </Label>
          <MultiSelect
            triggerId="filter-role"
            label="Target role"
            placeholder="Any role"
            options={options.roles}
            values={value.target_role}
            onChange={(roles) => update({ target_role: roles })}
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-source" className="mb-1.5 block text-xs text-muted-foreground">
            Source
          </Label>
          <MultiSelect
            triggerId="filter-source"
            label="Source"
            placeholder="Any source"
            options={options.sources}
            values={value.source}
            onChange={(sources) => update({ source: sources })}
            disabled={disabled}
          />
        </div>

        <div className="col-span-1">
          <Label htmlFor="filter-skills" className="mb-1.5 block text-xs text-muted-foreground">
            Skills
          </Label>
          <MultiSelect
            triggerId="filter-skills"
            label="Skills"
            placeholder="Any skill"
            options={options.skills}
            values={value.skills}
            onChange={(skills) => update({ skills })}
            disabled={disabled}
          />
        </div>

        <CommitInput
          id="filter-min-exp"
          label="Min experience"
          placeholder="0"
          rawValue={value.min_experience === undefined ? '' : String(value.min_experience)}
          disabled={disabled}
          onCommit={(minExperience) => update({ min_experience: minExperience })}
        />

        <CommitInput
          id="filter-max-exp"
          label="Max experience"
          placeholder="No limit"
          rawValue={value.max_experience === undefined ? '' : String(value.max_experience)}
          disabled={disabled}
          onCommit={(maxExperience) => update({ max_experience: maxExperience })}
        />

        <div className="col-span-1">
          <Label htmlFor="filter-shortlisted" className="mb-1.5 block text-xs text-muted-foreground">
            Shortlisted
          </Label>
          <Select
            value={shortlisted}
            onValueChange={(next) =>
              update({ is_shortlisted: next === 'any' ? undefined : next === 'true' })
            }
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

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {chips.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {chips.map((chip) => (
              <span
                key={chip.key}
                className="inline-flex items-center gap-1 border border-border bg-muted px-2 py-0.5 text-[11px] font-medium text-foreground"
              >
                {chip.label}
                <button
                  type="button"
                  onClick={chip.onRemove}
                  aria-label={`Remove ${chip.label} filter`}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <XIcon className="size-3" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <span />
        )}

        <Button variant="outline" size="sm" onClick={onClear} disabled={disabled || activeCount === 0}>
          Clear filters
        </Button>
      </div>
    </section>
  );
}

function experienceLabel(minExperience?: number, maxExperience?: number): string {
  if (minExperience !== undefined && maxExperience !== undefined) {
    return `${minExperience}–${maxExperience} yrs`;
  }
  if (minExperience !== undefined) {
    return `${minExperience}+ yrs`;
  }
  if (maxExperience !== undefined) {
    return `≤ ${maxExperience} yrs`;
  }
  return '';
}