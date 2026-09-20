import { useState } from 'react';
import { CaretDownIcon, CheckIcon } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

const MAX_PREVIEW = 2;

type MultiSelectProps = {
  triggerId?: string;
  label: string;
  placeholder: string;
  options: string[];
  values: string[];
  onChange: (values: string[]) => void;
  disabled?: boolean;
};

function summaryText(options: string[], values: string[], placeholder: string): string {
  if (values.length === 0) return placeholder;
  if (values.length === options.length) return 'All';
  const shown = values.slice(0, MAX_PREVIEW).join(', ');
  const extra = values.length - MAX_PREVIEW;
  return extra > 0 ? `${shown}, +${extra} more` : shown;
}

export function MultiSelect({
  triggerId,
  label,
  placeholder,
  options,
  values,
  onChange,
  disabled,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const isActive = values.length > 0;

  function toggle(value: string) {
    onChange(
      values.includes(value) ? values.filter((v) => v !== value) : [...values, value],
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        asChild
        disabled={disabled}
      >
        <button
          type="button"
          id={triggerId}
          aria-label={label}
          aria-expanded={open}
          className={cn(
            'flex h-8 w-full items-center justify-between gap-2 border border-input bg-background px-2.5 text-xs whitespace-nowrap transition-colors outline-none select-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50',
            isActive ? 'border-primary/50 text-foreground' : 'text-muted-foreground',
          )}
        >
          <span className="truncate">{summaryText(options, values, placeholder)}</span>
          <CaretDownIcon
            className={cn('size-3.5 shrink-0 transition-transform', open && 'rotate-180')}
          />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 p-1">
        <div
          role="listbox"
          aria-label={label}
          aria-multiselectable="true"
          className="max-h-60 overflow-y-auto"
        >
          {options.length === 0 ? (
            <p className="px-2 py-2 text-muted-foreground">No options available.</p>
          ) : (
            options.map((option) => {
              const checked = values.includes(option);
              return (
                <button
                  key={option}
                  type="button"
                  role="option"
                  aria-selected={checked}
                  onClick={() => toggle(option)}
                  className={cn(
                    'flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs hover:bg-muted',
                    checked && 'bg-muted/70',
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      'flex size-4 shrink-0 items-center justify-center border transition-colors',
                      checked
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-input bg-background',
                    )}
                  >
                    {checked ? <CheckIcon className="size-3" weight="bold" /> : null}
                  </span>
                  <span className="truncate">{option}</span>
                </button>
              );
            })
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}