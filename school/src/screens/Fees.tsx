import clsx from "clsx";
import { ChevronDown, ChevronRight, IndianRupee, Wallet } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { BackLink, Card, Chip, EmptyState, ErrorCard, SectionTitle, Skeleton } from "@/components/ui";
import { formatDay } from "@/lib/dates";
import { money } from "@/lib/format";
import { useDivisionFees, useFeeOverview } from "@/lib/queries";
import type { FeeDivision, FeeTotals, StudentFees } from "@/lib/types";

function pct(part: number, whole: number) {
  return whole ? Math.round((part / whole) * 100) : 0;
}

function CollectedBar({ totals }: { totals: FeeTotals }) {
  const paid = pct(totals.paid, totals.billed);
  const overdue = pct(totals.overdue, totals.billed);
  return (
    <span className="flex h-2 overflow-hidden rounded-full bg-line" aria-hidden>
      <span className="h-full bg-good" style={{ width: `${paid}%` }} />
      <span className="h-full bg-bad/80" style={{ width: `${overdue}%` }} />
    </span>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-semibold text-muted">{label}</p>
      <p className={clsx("tabular truncate text-lg font-extrabold", tone === "good" && "text-good", tone === "bad" && "text-bad")}>{value}</p>
    </div>
  );
}

export function Summary({ totals, currency }: { totals: FeeTotals; currency: string }) {
  return (
    <Card className="grid gap-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Collected" value={money(totals.paid, currency)} tone="good" />
        <Stat label="Overdue" value={money(totals.overdue, currency)} tone={totals.overdue ? "bad" : undefined} />
        <Stat label="Still to come" value={money(totals.outstanding - totals.overdue, currency)} />
      </div>
      <CollectedBar totals={totals} />
      <p className="text-xs text-muted">
        {pct(totals.paid, totals.billed)}% of {money(totals.billed, currency)} collected
        {totals.next_due_date && ` · next instalment due ${formatDay(totals.next_due_date)}`}
      </p>
    </Card>
  );
}

// ---------------------------------------------------------------- overview

function DivisionRow({ division, currency }: { division: FeeDivision; currency: string }) {
  return (
    <Link
      to={`/fees/${encodeURIComponent(division.name)}`}
      className="group grid gap-3 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[16px] font-bold">{division.student_group_name}</p>
          <p className={clsx("text-sm font-semibold", division.defaulters ? "text-bad" : "text-muted")}>
            {division.defaulters
              ? `${division.defaulters} of ${division.strength} overdue · ${money(division.overdue, currency)}`
              : division.billed
                ? "Nobody overdue"
                : "No fees raised yet"}
          </p>
        </div>
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted transition group-hover:translate-x-0.5" />
      </div>
      {division.billed > 0 && (
        <div className="grid gap-1.5">
          <CollectedBar totals={division} />
          <p className="tabular text-xs font-semibold text-muted">
            {money(division.paid, currency)} of {money(division.billed, currency)} collected
          </p>
        </div>
      )}
    </Link>
  );
}

export function FeesOverview() {
  const { data, isPending, error, refetch } = useFeeOverview();

  const totals = (data?.divisions ?? []).reduce<FeeTotals>(
    (acc, d) => ({
      billed: acc.billed + d.billed,
      paid: acc.paid + d.paid,
      outstanding: acc.outstanding + d.outstanding,
      overdue: acc.overdue + d.overdue,
      next_due_date:
        d.next_due_date && (!acc.next_due_date || d.next_due_date < acc.next_due_date) ? d.next_due_date : acc.next_due_date,
    }),
    { billed: 0, paid: 0, outstanding: 0, overdue: 0, next_due_date: null },
  );
  const worst = [...(data?.divisions ?? [])].sort((a, b) => b.overdue - a.overdue);

  return (
    <div>
      <PageTitle title="Fees" subtitle="Who has paid, and who is overdue" />
      {isPending ? (
        <div className="grid gap-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-24" />
        </div>
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.divisions.length === 0 ? (
        <EmptyState icon={<Wallet className="h-7 w-7" />} title="No classes to show">
          Fees appear here for the divisions you are class teacher of.
        </EmptyState>
      ) : (
        <div className="grid gap-6">
          {data.divisions.length > 1 && <Summary totals={totals} currency={data.currency} />}
          <section className="grid gap-3">
            <SectionTitle>Classes</SectionTitle>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {worst.map((d) => (
                <DivisionRow key={d.name} division={d} currency={data.currency} />
              ))}
            </div>
          </section>
          <p className="px-1 text-xs text-muted">
            Read-only. Payments and receipts are handled by the accounts office in the ERP.
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- division

type Filter = "overdue" | "due" | "paid" | "all";

const FILTERS: { key: Filter; label: string; match: (s: StudentFees) => boolean }[] = [
  { key: "overdue", label: "Overdue", match: (s) => s.overdue > 0 },
  { key: "due", label: "Due later", match: (s) => s.overdue === 0 && s.outstanding > 0 },
  { key: "paid", label: "Paid up", match: (s) => s.billed > 0 && s.outstanding === 0 },
  { key: "all", label: "Everyone", match: () => true },
];

function StudentRow({ student, currency }: { student: StudentFees; currency: string }) {
  const [open, setOpen] = useState(false);
  const status = student.overdue
    ? { text: `${money(student.overdue, currency)} overdue`, cls: "text-bad" }
    : student.outstanding
      ? { text: `${money(student.outstanding, currency)} due${student.next_due_date ? ` ${formatDay(student.next_due_date)}` : ""}`, cls: "text-warn" }
      : student.billed
        ? { text: "Paid up", cls: "text-good" }
        : { text: "No fees raised", cls: "text-muted" };

  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        disabled={!student.instalments.length}
        className="flex w-full items-center gap-3 px-4 py-3 text-left disabled:cursor-default"
      >
        <span className="tabular w-8 shrink-0 text-sm font-semibold text-muted">{student.roll_no || "–"}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[15px] font-bold">{student.student_name}</span>
          <span className={clsx("block truncate text-sm font-semibold", status.cls)}>{status.text}</span>
        </span>
        {student.instalments.length > 0 && (
          <ChevronDown className={clsx("h-5 w-5 shrink-0 text-muted transition-transform", open && "rotate-180")} />
        )}
      </button>
      {open && (
        <ul className="mx-4 mb-3 grid gap-1 rounded-2xl bg-bg p-2">
          {student.instalments.map((i, n) => (
            <li key={n} className="flex items-center gap-3 rounded-xl px-2 py-1.5 text-sm">
              <span className="min-w-0 flex-1 truncate font-semibold">{i.term || "Instalment"}</span>
              <span className="tabular text-muted">{i.due_date ? formatDay(i.due_date) : "—"}</span>
              <span className="tabular w-20 text-right font-semibold">{money(i.amount, currency)}</span>
              <span
                className={clsx(
                  "w-16 text-right text-xs font-bold uppercase",
                  i.paid ? "text-good" : i.overdue ? "text-bad" : "text-warn",
                )}
              >
                {i.paid ? "Paid" : i.overdue ? "Overdue" : "Due"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function DivisionFeesScreen() {
  const { division = "" } = useParams();
  const { data, isPending, error, refetch } = useDivisionFees(division);
  const [filter, setFilter] = useState<Filter>("overdue");

  const counts = Object.fromEntries(FILTERS.map((f) => [f.key, data?.students.filter(f.match).length ?? 0])) as Record<Filter, number>;
  // Land on the first list that has anyone in it.
  const active = counts[filter] || filter === "all" ? filter : (FILTERS.find((f) => counts[f.key])?.key ?? "all");
  const shown = data?.students.filter(FILTERS.find((f) => f.key === active)!.match) ?? [];

  return (
    <div>
      <PageTitle
        title={data?.division.student_group_name ?? "Fees"}
        subtitle={data?.academic_year ? `Fees for ${data.academic_year}` : undefined}
        back={<BackLink to="/fees">Fees</BackLink>}
      />
      {isPending ? (
        <div className="grid gap-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-64" />
        </div>
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.billed === 0 ? (
        <EmptyState icon={<IndianRupee className="h-7 w-7" />} title="No fees raised yet">
          Once the accounts office raises this year's fees for {data.division.student_group_name}, they'll show here.
        </EmptyState>
      ) : (
        <div className="grid gap-5">
          <Summary totals={data} currency={data.currency} />
          <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Show">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                role="tab"
                aria-selected={active === f.key}
                onClick={() => setFilter(f.key)}
                className={clsx(
                  "inline-flex h-10 shrink-0 items-center gap-1.5 rounded-full px-4 text-sm font-bold transition",
                  active === f.key ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line",
                )}
              >
                {f.label} <span className="tabular opacity-70">{counts[f.key]}</span>
              </button>
            ))}
          </div>
          {shown.length ? (
            <Card flush className="overflow-hidden">
              <ul className="divide-y divide-line">
                {shown.map((s) => (
                  <StudentRow key={s.student} student={s} currency={data.currency} />
                ))}
              </ul>
            </Card>
          ) : (
            <p className="px-1 text-sm text-muted">Nobody here.</p>
          )}
          <p className="flex items-center gap-2 px-1 text-xs text-muted">
            <Chip tone="muted">Read-only</Chip> Payments are recorded by the accounts office.
          </p>
        </div>
      )}
    </div>
  );
}
