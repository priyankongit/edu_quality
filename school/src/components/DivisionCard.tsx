import clsx from "clsx";
import { CheckCircle2, ChevronRight, PartyPopper } from "lucide-react";
import { Link } from "react-router-dom";
import type { Division } from "@/lib/types";

export function registerPath(division: string, date?: string) {
  const base = `/attendance/${encodeURIComponent(division)}`;
  return date ? `${base}?date=${date}` : base;
}

function StatusLine({ division }: { division: Division }) {
  const { attendance: a, holiday } = division;
  if (holiday)
    return (
      <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted">
        <PartyPopper className="h-4 w-4" /> Holiday
      </span>
    );
  if (a.submitted)
    return (
      <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-good">
        <CheckCircle2 className="h-4 w-4" /> Submitted · {a.present} present, {a.absent} absent
      </span>
    );
  if (a.marked)
    return <span className="text-sm font-semibold text-warn">Draft · {a.marked} of {a.strength} marked</span>;
  return <span className="text-sm font-semibold text-muted">Attendance not taken</span>;
}

export default function DivisionCard({ division, date }: { division: Division; date?: string }) {
  const { attendance: a } = division;
  const pct = a.strength ? Math.round((a.marked / a.strength) * 100) : 0;
  return (
    <Link
      to={registerPath(division.name, date)}
      className="group flex items-center gap-4 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40"
    >
      <span
        className={clsx(
          "grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-lg font-extrabold tracking-tight",
          a.submitted ? "bg-good/10 text-good" : "bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft",
        )}
      >
        {division.student_group_name.split(/[\s(]/)[0]}
      </span>
      <span className="grid min-w-0 flex-1 gap-1">
        <span className="truncate text-[16px] font-bold">{division.student_group_name}</span>
        <StatusLine division={division} />
        {!a.submitted && !division.holiday && a.strength > 0 && (
          <span className="mt-1 h-1.5 overflow-hidden rounded-full bg-line" aria-hidden>
            <span className="block h-full rounded-full bg-brand transition-all" style={{ width: `${pct}%` }} />
          </span>
        )}
      </span>
      <span className="grid shrink-0 justify-items-end gap-1">
        <span className="tabular text-xs font-semibold text-muted">{a.strength} students</span>
        <ChevronRight className="h-5 w-5 text-muted transition group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
