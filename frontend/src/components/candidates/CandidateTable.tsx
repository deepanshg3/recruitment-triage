import {
  CaretDownIcon,
  CaretUpIcon,
  CaretUpDownIcon,
} from '@phosphor-icons/react';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { formatAppliedDate, formatYears } from '@/lib/format';
import type { ActiveSort, Candidate, CandidateSortField } from '@/lib/types';
import { ShortlistButton } from './ShortlistButton';

const columnHelper = createColumnHelper<Candidate>();

const NAMED_COLUMNS = new Set<CandidateSortField>(['name', 'target_role', 'years_experience', 'applied_date']);

const PRIORITY_MARKS = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];

type SortHeaderProps = {
  label: string;
  id: CandidateSortField;
  sorts: ActiveSort[];
  onSortChange: (field: CandidateSortField) => void;
};

function SortHeader({ label, id, sorts, onSortChange }: SortHeaderProps) {
  const index = sorts.findIndex((sort) => sort.field === id);
  const isActive = index !== -1;
  const direction = isActive ? sorts[index].direction : null;
  const Icon = direction === 'asc' ? CaretUpIcon : direction === 'desc' ? CaretDownIcon : CaretUpDownIcon;
  const next = direction === null ? 'asc' : direction === 'asc' ? 'desc' : 'asc';

  return (
    <button
      type="button"
      onClick={() => onSortChange(id)}
      aria-label={`Sort by ${label} ${next === 'asc' ? 'ascending' : 'descending'}`}
      className="group inline-flex items-center gap-1 uppercase hover:text-foreground"
    >
      {label}
      {isActive ? (
        <>
          <span className="text-[10px] leading-none text-primary">
            {PRIORITY_MARKS[index] ?? String(index + 1)}
          </span>
          <Icon
            className="size-3.5 text-primary"
            weight="fill"
          />
        </>
      ) : (
        <Icon
          className="size-3.5 text-muted-foreground/60 group-hover:text-muted-foreground"
          weight="regular"
        />
      )}
    </button>
  );
}

type CandidateTableProps = {
  candidates: Candidate[];
  sorts: ActiveSort[];
  onSortChange: (field: CandidateSortField) => void;
  onSelectCandidate: (candidate: Candidate) => void;
  onToggleShortlist: (candidate: Candidate) => void;
  disabled?: boolean;
};

export function CandidateTable({
  candidates,
  sorts,
  onSortChange,
  onSelectCandidate,
  onToggleShortlist,
  disabled,
}: CandidateTableProps) {
  const sorting = sorts.map((sort) => ({ id: sort.field, desc: sort.direction === 'desc' }));

  const columns = [
    columnHelper.display({
      id: 'shortlist',
      header: () => (
        <span className="sr-only">Shortlist</span>
      ),
      cell: ({ row }) => (
        <ShortlistButton
          candidate={row.original}
          onToggle={onToggleShortlist}
          disabled={disabled}
        />
      ),
      enableSorting: false,
      meta: { className: 'w-10' },
    }),
    columnHelper.accessor('name', {
      id: 'name',
      header: () => <SortHeader label="Name" id="name" sorts={sorts} onSortChange={onSortChange} />,
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => onSelectCandidate(row.original)}
          className="text-left text-sm font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
        >
          {row.original.name}
        </button>
      ),
    }),
    columnHelper.accessor('target_role', {
      id: 'target_role',
      header: () => <SortHeader label="Role" id="target_role" sorts={sorts} onSortChange={onSortChange} />,
      cell: ({ row }) => <span className="text-sm text-foreground">{row.original.target_role}</span>,
    }),
    columnHelper.accessor('years_experience', {
      id: 'years_experience',
      header: () => <SortHeader label="Experience" id="years_experience" sorts={sorts} onSortChange={onSortChange} />,
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground tabular-nums">
          {formatYears(row.original.years_experience)}
        </span>
      ),
    }),
    columnHelper.accessor('skills', {
      id: 'skills',
      header: () => <span className="uppercase">Skills</span>,
      enableSorting: false,
      cell: ({ row }) => <SkillsCell skills={row.original.skills} />,
    }),
    columnHelper.accessor('source', {
      id: 'source',
      header: () => <span className="uppercase">Source</span>,
      enableSorting: false,
      cell: ({ row }) => <span className="text-sm text-foreground">{row.original.source}</span>,
    }),
    columnHelper.accessor('applied_date', {
      id: 'applied_date',
      header: () => <SortHeader label="Applied" id="applied_date" sorts={sorts} onSortChange={onSortChange} />,
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground tabular-nums">
          {formatAppliedDate(row.original.applied_date)}
        </span>
      ),
    }),
  ];

  const table = useReactTable({
    data: candidates,
    columns,
    state: { sorting },
    manualSorting: true,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => String(row.id),
  });

  const headerGroups = table.getHeaderGroups();
  const rows = table.getRowModel().rows;

  if (candidates.length === 0) {
    return (
      <div className="border border-border bg-card p-12 text-center">
        <p className="text-sm text-muted-foreground">No candidates found.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-border bg-card">
      <Table className="min-w-[760px]">
        <TableHeader>
          {headerGroups.map((headerGroup) => (
            <TableRow key={headerGroup.id} className="border-b border-border bg-muted/50 hover:bg-muted/50">
              {headerGroup.headers.map((header) => {
                const activeIndex = sorts.findIndex((s) => s.field === header.id);
                const ariaSort =
                  activeIndex === -1
                    ? undefined
                    : sorts[activeIndex].direction === 'asc'
                      ? 'ascending'
                      : 'descending';
                return (
                  <TableHead
                    key={header.id}
                    className={`h-9 px-3 text-[11px] font-semibold tracking-wide text-muted-foreground ${
                      NAMED_COLUMNS.has(header.id as CandidateSortField) ? 'cursor-pointer select-none' : ''
                    } ${String((header.column.columnDef.meta as { className?: string } | undefined)?.className ?? '')}`}
                    aria-sort={ariaSort}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow
              key={row.id}
              data-state={row.original.is_shortlisted ? 'shortlisted' : undefined}
              className="hover:bg-muted/40 data-[state=shortlisted]:bg-primary/[0.04]"
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell
                  key={cell.id}
                  className={`px-3 py-2.5 align-middle ${
                    String((cell.column.columnDef.meta as { className?: string } | undefined)?.className ?? '')
                  }`}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function SkillsCell({ skills }: { skills: string[] }) {
  const visible = skills.slice(0, 3);
  const extra = skills.length - visible.length;

  return (
    <div className="flex max-w-[260px] flex-wrap items-center gap-1">
      {visible.map((skill) => (
        <Badge key={skill} variant="secondary" className="text-[11px]">
          {skill}
        </Badge>
      ))}
      {extra > 0 ? (
        <span className="text-[11px] font-medium text-muted-foreground">+{extra}</span>
      ) : null}
    </div>
  );
}