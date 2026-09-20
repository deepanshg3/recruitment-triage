import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { CandidatesPage } from '@/pages/CandidatesPage';

export default App;

function App() {
  return (
    <TooltipProvider delayDuration={150}>
      <CandidatesPage />
      <Toaster position="top-right" richColors />
    </TooltipProvider>
  );
}