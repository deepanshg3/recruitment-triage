import { SparkleIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

type HeaderProps = {
  onOpenMatch: () => void;
};

export function Header({ onOpenMatch }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <img
            src="/logo/gccx-logo.png"
            alt="GCCX logo"
            className="h-9 w-auto"
            width={36}
            height={36}
          />
          <div className="leading-tight">
            <h1 className="text-sm font-semibold tracking-tight text-foreground">
              Candidate Triage
            </h1>
            <p className="text-xs text-muted-foreground">Recruitment intelligence for GCCX</p>
          </div>
        </div>

        <Button variant="default" onClick={onOpenMatch}>
          <SparkleIcon className="size-4" />
          AI Match
        </Button>
      </div>
    </header>
  );
}