import { useState } from 'react';
import { SparkleIcon, WarningCircleIcon } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

const TOP_K_OPTIONS = [1, 3, 5, 10, 15, 20, 30, 50];

type MatchDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (jobDescription: string, topK: number) => void;
  loading: boolean;
  error: string | null;
};

export function MatchDialog({ open, onOpenChange, onSubmit, loading, error }: MatchDialogProps) {
  const [jobDescription, setJobDescription] = useState('');
  const [topK, setTopK] = useState('5');

  function reset() {
    setJobDescription('');
    setTopK('5');
  }

  function handleOpenChange(next: boolean) {
    if (loading) return;
    onOpenChange(next);
    if (!next) reset();
  }

  function handleSubmit() {
    if (loading) return;
    const trimmed = jobDescription.trim();
    if (!trimmed) return;
    onSubmit(trimmed, Number(topK));
  }

  const canSubmit = !loading && jobDescription.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <SparkleIcon className="size-4 text-primary" />
            AI Match candidates
          </DialogTitle>
          <DialogDescription>
            Paste a job description and we'll rank your candidate pool by semantic similarity and
            screen the closest matches with AI.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-1">
          <div>
            <Label htmlFor="job-description" className="mb-1.5 block text-xs text-muted-foreground">
              Job description
            </Label>
            <Textarea
              id="job-description"
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the job description or role requirements here…"
              rows={6}
              disabled={loading}
            />
          </div>

          <div className="max-w-[180px]">
            <Label htmlFor="top-k" className="mb-1.5 block text-xs text-muted-foreground">
              Candidates to screen
            </Label>
            <Select value={topK} onValueChange={setTopK} disabled={loading}>
              <SelectTrigger id="top-k" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TOP_K_OPTIONS.map((value) => (
                  <SelectItem key={value} value={String(value)}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error ? (
            <div className="flex items-start gap-2 border border-destructive/30 bg-destructive/5 px-3 py-2" role="alert">
              <WarningCircleIcon className="mt-0.5 size-4 shrink-0 text-destructive" weight="fill" />
              <p className="text-xs leading-relaxed text-destructive">{error}</p>
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button variant="default" onClick={handleSubmit} disabled={!canSubmit}>
            {loading ? (
              <>
                <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Analyzing candidates…
              </>
            ) : (
              <>
                <SparkleIcon className="size-4" />
                Find candidates
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}