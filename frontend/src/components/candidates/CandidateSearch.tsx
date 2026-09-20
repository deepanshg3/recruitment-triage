import { MagnifyingGlassIcon, XIcon } from '@phosphor-icons/react';
import { Input } from '@/components/ui/input';

type CandidateSearchProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

export function CandidateSearch({ value, onChange, disabled }: CandidateSearchProps) {
  return (
    <div className="relative w-full max-w-sm">
      <MagnifyingGlassIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search candidates…"
        aria-label="Search candidates"
        className="pl-9 pr-8"
        disabled={disabled}
      />
      {value ? (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded-none p-0.5 text-muted-foreground hover:text-foreground"
        >
          <XIcon className="size-3.5" />
        </button>
      ) : null}
    </div>
  );
}