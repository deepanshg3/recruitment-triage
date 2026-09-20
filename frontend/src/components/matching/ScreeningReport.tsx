import {
  CheckCircleIcon,
  QuestionIcon,
  QuotesIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react';
import type { ScreeningReport as ScreeningReportType } from '@/lib/types';

function Section({
  icon,
  title,
  color,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  color: 'green' | 'amber' | 'default' | 'muted';
  children: React.ReactNode;
}) {
  const iconClass =
    color === 'green'
      ? 'text-primary'
      : color === 'amber'
        ? 'text-[#a3793b]'
        : color === 'muted'
          ? 'text-muted-foreground'
          : 'text-foreground';

  return (
    <section>
      <h3 className={`mb-2 flex items-center gap-1.5 text-[11px] font-semibold tracking-wide uppercase ${iconClass}`}>
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

export function ScreeningReport({ report }: { report: ScreeningReportType }) {
  return (
    <div className="space-y-5">
      {report.overall_assessment ? (
        <p className="text-sm leading-relaxed text-foreground">{report.overall_assessment}</p>
      ) : null}

      {report.strengths.length > 0 ? (
        <Section icon={<CheckCircleIcon className="size-4" weight="fill" />} title="Strengths" color="green">
          <ul className="space-y-1.5">
            {report.strengths.map((item, index) => (
              <li key={`s-${index}`} className="text-sm leading-relaxed text-foreground">
                {item}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {report.gaps.length > 0 ? (
        <Section icon={<WarningCircleIcon className="size-4" weight="fill" />} title="Gaps" color="amber">
          <ul className="space-y-1.5">
            {report.gaps.map((item, index) => (
              <li key={`g-${index}`} className="text-sm leading-relaxed text-[#7a5a28]">
                {item}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {report.evidence.length > 0 ? (
        <Section icon={<QuotesIcon className="size-4" />} title="Evidence" color="muted">
          <ul className="space-y-2">
            {report.evidence.map((item, index) => (
              <li
                key={`e-${index}`}
                className="border-l-2 border-border bg-muted/50 px-3 py-2 text-sm leading-relaxed text-muted-foreground italic"
              >
                {item}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {report.interview_questions.length > 0 ? (
        <Section icon={<QuestionIcon className="size-4" />} title="Interview questions" color="default">
          <ol className="space-y-1.5">
            {report.interview_questions.map((question, index) => (
              <li key={`q-${index}`} className="flex gap-2 text-sm leading-relaxed text-foreground">
                <span className="font-medium text-primary tabular-nums">{index + 1}.</span>
                <span>{question}</span>
              </li>
            ))}
          </ol>
        </Section>
      ) : null}
    </div>
  );
}