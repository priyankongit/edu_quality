import clsx from "clsx";
import { BookOpenCheck, CalendarCheck2, CalendarClock, CheckCircle2, ChevronLeft, ChevronRight, CircleDashed, Paperclip, Wallet } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { BackLink, Card, Chip, EmptyState, ErrorCard, SectionTitle, Skeleton } from "@/components/ui";
import { formatDay, localISO, minutesOf, parseISO } from "@/lib/dates";
import { fileUrl } from "@/lib/frappe";
import { money } from "@/lib/format";
import { useStudentAttendance, useStudentFees, useStudentHome, useStudentHomework, useStudentHomeworkDetail } from "@/lib/queries";
import type { AttendanceDay, AttendanceTotals, HomeworkStatus, StudentHome as Home, StudentHomework } from "@/lib/types";
import { ComingUp } from "@/screens/Calendar";
import { Summary } from "@/screens/Fees";

function greeting(date: Date) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function dueLabel(iso: string) {
  const days = Math.round((parseISO(iso).getTime() - parseISO(localISO()).getTime()) / 86_400_000);
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  if (days > 1 && days < 7) return `Due ${formatDay(iso, { weekday: "long" })}`;
  if (days < 0) return `Was due ${formatDay(iso)}`;
  return `Due ${formatDay(iso)}`;
}

function plainText(html: string | null) {
  if (!html) return "";
  return new DOMParser().parseFromString(html.replace(/<br\s*\/?>/gi, "\n").replace(/<\/p>/gi, "\n"), "text/html").body.textContent?.trim() ?? "";
}

const HW_STATUS: Record<HomeworkStatus, { label: string; cls: string; icon: typeof CheckCircle2 }> = {
  Pending: { label: "To do", cls: "text-warn", icon: CircleDashed },
  Submitted: { label: "Handed in", cls: "text-good", icon: CheckCircle2 },
  Reviewed: { label: "Checked", cls: "text-good", icon: CheckCircle2 },
};

// ---------------------------------------------------------------- home

function Hero({ home }: { home: Home }) {
  const s = home.student;
  const first = s.student_name.split(" ")[0];
  const today = home.holiday
    ? "Holiday today"
    : home.today
      ? `Marked ${home.today.status.toLowerCase()} today`
      : "Attendance not taken yet today";
  return (
    <section className="relative overflow-hidden rounded-4xl bg-brand p-5 text-on-brand shadow-float shadow-brand/30 md:p-6">
      <div aria-hidden className="absolute -right-10 -top-12 h-44 w-44 rounded-full bg-white/10" />
      <div aria-hidden className="absolute -bottom-16 right-16 h-32 w-32 rounded-full bg-white/10" />
      <p className="relative text-sm font-semibold opacity-80">{greeting(new Date())},</p>
      <p className="relative text-[26px] font-extrabold leading-tight tracking-tight md:text-3xl">{first}</p>
      <p className="relative mt-1 text-sm opacity-85">
        {s.division_name}
        {s.roll_no && ` · Roll ${s.roll_no}`}
      </p>
      <div className="relative mt-5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-semibold">
        <span>{today}</span>
        {home.attendance.percent !== null && <span className="tabular opacity-85">{home.attendance.percent}% attendance this year</span>}
      </div>
    </section>
  );
}

function Periods({ home }: { home: Home }) {
  const now = new Date();
  const mins = now.getHours() * 60 + now.getMinutes();
  if (!home.periods.length)
    return (
      <EmptyState icon={<CalendarClock className="h-7 w-7" />} title="No periods today">
        Nothing is timetabled for {home.weekday}.
      </EmptyState>
    );
  return (
    <Card flush className="p-2">
      <ol className="grid">
        {home.periods.map((p) => {
          const current = mins >= minutesOf(p.from_time) && mins < minutesOf(p.to_time);
          const past = mins >= minutesOf(p.to_time);
          return (
            <li key={p.name} className={clsx("flex items-center gap-3 rounded-2xl px-3 py-2.5", current && "bg-brand-soft dark:bg-brand/25", past && "opacity-55")}>
              <span className="tabular w-[92px] shrink-0 text-sm font-semibold text-muted">
                {p.from_time}–{p.to_time}
              </span>
              <span className="min-w-0 flex-1 truncate text-[15px] font-bold">{p.subject_name || p.subject}</span>
              {current && <Chip>Now</Chip>}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

function HomeworkCard({ hw }: { hw: StudentHomework }) {
  const status = HW_STATUS[hw.status];
  const overdue = hw.status === "Pending" && hw.due_date < localISO();
  return (
    <Link
      to={`/homework/${encodeURIComponent(hw.name)}`}
      className="group flex items-start gap-3 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40"
    >
      <div className="min-w-0 flex-1">
        {hw.subject_name && (
          <div className="mb-1.5">
            <Chip>{hw.subject_name}</Chip>
          </div>
        )}
        <p className="truncate text-[16px] font-bold">{hw.title}</p>
        <p className="flex items-center gap-2 text-sm font-semibold">
          <span className={overdue ? "text-bad" : "text-muted"}>{dueLabel(hw.due_date)}</span>
          <span className={clsx("inline-flex items-center gap-1", status.cls)}>
            <status.icon className="h-4 w-4" /> {status.label}
          </span>
        </p>
      </div>
      <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted transition group-hover:translate-x-0.5" />
    </Link>
  );
}

function FeeCard({ home }: { home: Home }) {
  const f = home.fees;
  if (!f.billed) return null;
  const text = f.overdue
    ? { line: `${money(f.overdue, f.currency)} overdue`, cls: "text-bad" }
    : f.outstanding
      ? { line: `${money(f.outstanding, f.currency)} due${f.next_due_date ? ` by ${formatDay(f.next_due_date)}` : ""}`, cls: "text-warn" }
      : { line: "All fees paid", cls: "text-good" };
  return (
    <Link to="/fees" className="flex items-center gap-3 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40">
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft">
        <Wallet className="h-[22px] w-[22px]" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-bold">Fees</span>
        <span className={clsx("block truncate text-sm font-semibold", text.cls)}>{text.line}</span>
      </span>
      <ChevronRight className="h-5 w-5 text-muted" />
    </Link>
  );
}

export function StudentHome() {
  const { data, isPending, error, refetch } = useStudentHome();
  const dateLabel = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <div>
      <PageTitle title="Today" subtitle={dateLabel} />
      {isPending ? (
        <div className="grid gap-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-24" />
        </div>
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 lg:items-start">
          <div className="grid min-w-0 grid-cols-1 gap-6 lg:col-span-3">
            <Hero home={data} />
            <section className="grid gap-3">
              <SectionTitle
                action={
                  <Link to="/homework" className="text-sm font-semibold text-brand dark:text-brand-soft">
                    All homework
                  </Link>
                }
              >
                Homework to do
              </SectionTitle>
              {data.homework_due.length ? (
                data.homework_due.map((h) => <HomeworkCard key={h.name} hw={h} />)
              ) : (
                <Card className="flex items-center gap-3 text-sm text-muted">
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-good" /> Nothing due. Nice work.
                </Card>
              )}
            </section>
            <FeeCard home={data} />
          </div>
          <div className="grid min-w-0 grid-cols-1 gap-6 lg:col-span-2">
            <section className="grid gap-3">
              <SectionTitle>Timetable</SectionTitle>
              <Periods home={data} />
            </section>
            <ComingUp />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- homework

export function MyHomeworkList() {
  const { data, isPending, error, refetch } = useStudentHomework();
  const today = localISO();
  const todo = data?.filter((h) => h.open && h.status === "Pending" && h.due_date >= today) ?? [];
  const rest = data?.filter((h) => !todo.includes(h)) ?? [];

  return (
    <div>
      <PageTitle title="Homework" subtitle="Set by your teachers" />
      {isPending ? (
        <Skeleton className="h-40" />
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.length === 0 ? (
        <EmptyState icon={<BookOpenCheck className="h-7 w-7" />} title="No homework yet">
          Homework your teachers set for your class will show here.
        </EmptyState>
      ) : (
        <div className="grid gap-6">
          {todo.length > 0 && (
            <section className="grid gap-3">
              <SectionTitle>To do</SectionTitle>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {todo.map((h) => (
                  <HomeworkCard key={h.name} hw={h} />
                ))}
              </div>
            </section>
          )}
          {rest.length > 0 && (
            <section className="grid gap-3">
              <SectionTitle>Earlier</SectionTitle>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {rest.map((h) => (
                  <HomeworkCard key={h.name} hw={h} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

export function MyHomeworkDetail() {
  const { name = "" } = useParams();
  const { data, isPending, error, refetch } = useStudentHomeworkDetail(name);
  const status = data && HW_STATUS[data.status];

  return (
    <div>
      <PageTitle title={data?.title ?? "Homework"} subtitle={data ? dueLabel(data.due_date) : undefined} back={<BackLink to="/homework">Homework</BackLink>} />
      {isPending ? (
        <Skeleton className="h-48" />
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : (
        <div className="grid gap-4">
          <Card className="grid gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              {data.subject_name && <Chip>{data.subject_name}</Chip>}
              {!data.open && <Chip tone="muted">Closed</Chip>}
              {status && (
                <span className={clsx("ml-auto inline-flex items-center gap-1 text-sm font-bold", status.cls)}>
                  <status.icon className="h-4 w-4" /> {status.label}
                </span>
              )}
            </div>
            {data.instructions ? (
              <p className="whitespace-pre-line text-[15px] leading-relaxed">{plainText(data.instructions)}</p>
            ) : (
              <p className="text-sm text-muted">No extra instructions.</p>
            )}
            {data.attachment && (
              <a href={fileUrl(data.attachment)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm font-semibold text-brand dark:text-brand-soft">
                <Paperclip className="h-4 w-4" /> Open attachment
              </a>
            )}
            <p className="text-xs text-muted">
              Set {formatDay(data.assigned_on)}
              {data.teacher && ` by ${data.teacher}`}
            </p>
          </Card>
          {data.remarks && (
            <Card className="grid gap-1">
              <p className="text-xs font-bold uppercase tracking-wide text-muted">Teacher's note</p>
              <p className="text-[15px]">{data.remarks}</p>
            </Card>
          )}
          <p className="px-1 text-xs text-muted">Hand your work in to your teacher; they mark it here once they've checked it.</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- attendance

function shiftMonth(month: string, by: number) {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + by, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function Totals({ label, totals }: { label: string; totals: AttendanceTotals }) {
  return (
    <Card className="grid gap-1">
      <p className="text-xs font-semibold text-muted">{label}</p>
      <p className="tabular text-2xl font-extrabold">{totals.percent === null ? "—" : `${totals.percent}%`}</p>
      <p className="tabular text-xs text-muted">
        {totals.present} present · {totals.absent} absent
      </p>
    </Card>
  );
}

export function MyAttendance() {
  const [params, setParams] = useSearchParams();
  const month = params.get("month") || localISO().slice(0, 7);
  const { data, isPending, error, refetch } = useStudentAttendance(month);
  const [y, m] = month.split("-").map(Number);
  const first = new Date(y, m - 1, 1);
  const daysInMonth = new Date(y, m, 0).getDate();
  const lead = (first.getDay() + 6) % 7; // weeks start on Monday
  const byDate = new Map<string, AttendanceDay>((data?.days ?? []).map((d) => [d.date, d]));
  const holidays = new Set(data?.holidays ?? []);
  const today = localISO();

  return (
    <div>
      <PageTitle title="Attendance" subtitle="Your days in school" />
      {error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3">
            {data ? <Totals label="This month" totals={data.month_totals} /> : <Skeleton className="h-24" />}
            {data ? <Totals label="This year" totals={data.year_totals} /> : <Skeleton className="h-24" />}
          </div>

          <Card className="grid gap-3">
            <div className="flex items-center gap-2">
              <button type="button" aria-label="Previous month" onClick={() => setParams({ month: shiftMonth(month, -1) })} className="grid h-10 w-10 place-items-center rounded-2xl hover:bg-bg">
                <ChevronLeft className="h-5 w-5" />
              </button>
              <p className="flex-1 text-center text-[16px] font-bold">{first.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</p>
              <button type="button" aria-label="Next month" onClick={() => setParams({ month: shiftMonth(month, 1) })} className="grid h-10 w-10 place-items-center rounded-2xl hover:bg-bg">
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
            {isPending ? (
              <Skeleton className="h-64" />
            ) : (
              <div className="grid grid-cols-7 gap-1.5 text-center" role="grid" aria-label="Attendance this month">
                {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
                  <span key={i} className="pb-1 text-xs font-bold text-muted">
                    {d}
                  </span>
                ))}
                {Array.from({ length: lead }, (_, i) => (
                  <span key={`lead-${i}`} />
                ))}
                {Array.from({ length: daysInMonth }, (_, i) => {
                  const iso = `${month}-${String(i + 1).padStart(2, "0")}`;
                  const mark = byDate.get(iso);
                  const holiday = holidays.has(iso);
                  return (
                    <span
                      key={iso}
                      title={mark ? `${formatDay(iso)}: ${mark.status}` : holiday ? `${formatDay(iso)}: Holiday` : formatDay(iso)}
                      className={clsx(
                        "tabular grid aspect-square place-items-center rounded-xl text-sm font-semibold",
                        !mark && !holiday && "text-muted",
                        holiday && !mark && "bg-warn/10 text-warn",
                        iso === today && "ring-2 ring-brand",
                      )}
                      style={mark?.color ? { backgroundColor: `${mark.color}22`, color: mark.color } : undefined}
                    >
                      {i + 1}
                    </span>
                  );
                })}
              </div>
            )}
            {data && (
              <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 text-xs text-muted">
                {data.statuses.map((s) => (
                  <span key={s.name} className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color || "currentColor" }} /> {s.name}
                  </span>
                ))}
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-warn/40" /> Holiday
                </span>
              </div>
            )}
          </Card>
          {data && data.days.length === 0 && (
            <p className="flex items-center gap-2 px-1 text-sm text-muted">
              <CalendarCheck2 className="h-4 w-4" /> No attendance recorded this month yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- fees

export function MyFeesScreen() {
  const { data, isPending, error, refetch } = useStudentFees();
  return (
    <div>
      <PageTitle title="Fees" subtitle={data ? `For ${data.academic_year}` : undefined} />
      {isPending ? (
        <Skeleton className="h-48" />
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.billed === 0 ? (
        <EmptyState icon={<Wallet className="h-7 w-7" />} title="No fees yet">
          Your fees for {data.academic_year} haven't been raised yet.
        </EmptyState>
      ) : (
        <div className="grid gap-5">
          <Summary totals={data} currency={data.currency} />
          <section className="grid gap-3">
            <SectionTitle>Instalments</SectionTitle>
            <Card flush className="overflow-hidden">
              <ul className="divide-y divide-line">
                {data.instalments.map((i, n) => (
                  <li key={n} className="flex items-center gap-3 px-4 py-3.5">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[15px] font-bold">{i.term || "Instalment"}</span>
                      <span className="block text-sm text-muted">{i.due_date ? `Due ${formatDay(i.due_date, { day: "numeric", month: "long", year: "numeric" })}` : "No due date"}</span>
                    </span>
                    <span className="text-right">
                      <span className="tabular block text-[15px] font-bold">{money(i.amount, data.currency)}</span>
                      <span className={clsx("block text-xs font-bold uppercase", i.paid ? "text-good" : i.overdue ? "text-bad" : "text-warn")}>
                        {i.paid ? "Paid" : i.overdue ? "Overdue" : "Due"}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </section>
          <p className="px-1 text-xs text-muted">To pay, use the payment link the school sends to your parents, or pay at the school office.</p>
        </div>
      )}
    </div>
  );
}
