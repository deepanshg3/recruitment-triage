import { MagnifyingGlassIcon, XIcon } from '@phosphor-icons/react';
import { Input } from '@/components/ui/input';

type CandidateSearchProps = {
  /** Draft text; typing does not trigger a request. */
  value: string;
  /** Update the draft only. */
  onChange: (value: string) => void;
  /** Commit a search on Enter. */
  onSubmit: (value: string) => void;
  /** Clear the search and refresh the list. */
  onClear: () => void;
  disabled?: boolean;
};

export function CandidateSearch({
  value,
  onChange,
  onSubmit,
  onClear,
  disabled,
}: CandidateSearchProps) {
  return (
    <form
      role="search"
      className="relative w-full max-w-sm"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(value.trim());
      }}
    >
      <MagnifyingGlassIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search candidates, press Enter to search"
        aria-label="Search candidates"
        className="pr-8 pl-9"
        disabled={disabled}
      />
      {value ? (
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear search"
          className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded-none p-0.5 text-muted-foreground hover:text-foreground"
        >
          <XIcon className="size-3.5" />
        </button>
      ) : null}
    </form>
  );
}