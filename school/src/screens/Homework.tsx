import clsx from "clsx";
import { BookOpenCheck, CalendarDays, Check, CheckCheck, ChevronLeft, ChevronRight, CircleDashed, MessageSquareText, Plus, Sparkles, Star } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { Button, Card, Chip, EmptyState, SectionTitle, Skeleton } from "@/components/ui";
import { formatDay, localISO, parseISO } from "@/lib/dates";
import { useCreateHomework, useHomework, useHomeworkForm, useHomeworkList, useMyDay, useUpdateHomework } from "@/lib/queries";
import type { HomeworkStatus, HomeworkSummary } from "@/lib/types";

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

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card className="text-sm">
      <p className="font-semibold text-bad">{message}</p>
      <button type="button" onClick={onRetry} className="mt-2 font-semibold text-brand dark:text-brand-soft">
        Try again
      </button>
    </Card>
  );
}

// ---------------------------------------------------------------- list

function HomeworkCard({ hw }: { hw: HomeworkSummary }) {
  const pct = hw.total ? Math.round((hw.submitted / hw.total) * 100) : 0;
  const overdue = hw.due_date < localISO() && hw.status === "Open";
  return (
    <Link
      to={`/homework/${encodeURIComponent(hw.name)}`}
      className="group grid gap-3 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            {hw.subject_name && <Chip>{hw.subject_name}</Chip>}
            <Chip tone="muted">{hw.division_name}</Chip>
            {hw.status === "Closed" && <Chip tone="muted">Closed</Chip>}
          </div>
          <p className="truncate text-[16px] font-bold">{hw.title}</p>
          <p className={clsx("text-sm font-semibold", overdue ? "text-warn" : "text-muted")}>{dueLabel(hw.due_date)}</p>
        </div>
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted transition group-hover:translate-x-0.5" />
      </div>
      <div className="flex items-center gap-3">
        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line" aria-hidden>
          <span className="block h-full rounded-full bg-good" style={{ width: `${pct}%` }} />
        </span>
        <span className="tabular shrink-0 text-xs font-semibold text-muted">
          {hw.submitted}/{hw.total} handed in
        </span>
      </div>
    </Link>
  );
}

export function HomeworkList() {
  const { data, isPending, error, refetch } = useHomeworkList();
  const today = localISO();
  const current = data?.filter((h) => h.status === "Open" && h.due_date >= today) ?? [];
  const past = data?.filter((h) => !(h.status === "Open" && h.due_date >= today)) ?? [];

  const newButton = (
    <Link to="/homework/new" className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-2xl bg-brand px-4 text-sm font-bold text-on-brand shadow-float shadow-brand/30 active:scale-95">
      <Plus className="h-4 w-4" /> New
    </Link>
  );

  return (
    <div>
      <PageTitle title="Homework" subtitle="Set, collect and check" action={newButton} />
      {isPending ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.length === 0 ? (
        <EmptyState icon={<BookOpenCheck className="h-7 w-7" />} title="No homework yet">
          Tap New to set homework for one of your classes. You can start from today's CMAP plan.
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {current.length > 0 && (
            <section className="grid grid-cols-1 gap-3">
              <SectionTitle>Due</SectionTitle>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {current.map((h) => (
                  <HomeworkCard key={h.name} hw={h} />
                ))}
              </div>
            </section>
          )}
          {past.length > 0 && (
            <section className="grid grid-cols-1 gap-3">
              <SectionTitle>Earlier</SectionTitle>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {past.map((h) => (
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

// ---------------------------------------------------------------- new

function tomorrow() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return localISO(d);
}

const inputCls =
  "w-full rounded-2xl bg-card px-4 text-base ring-1 ring-line placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-brand";

export function NewHomework() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { data: day } = useMyDay();
  const divisions = day?.divisions ?? [];
  const [division, setDivision] = useState(params.get("division") || "");
  const [subject, setSubject] = useState("");
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [due, setDue] = useState(tomorrow());
  const [cmap, setCmap] = useState<string | undefined>();
  const [error, setError] = useState("");
  const form = useHomeworkForm(division);
  const create = useCreateHomework();

  useEffect(() => {
    if (!division && divisions.length === 1) setDivision(divisions[0].name);
  }, [division, divisions]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!division) return setError("Choose a class.");
    if (!title.trim()) return setError("Give the homework a title.");
    setError("");
    try {
      const hw = await create.mutateAsync({ division, title: title.trim(), due_date: due, subject: subject || undefined, instructions, cmap });
      navigate(`/homework/${encodeURIComponent(hw.name)}`, { replace: true });
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const back = (
    <Link to="/homework" className="mb-1 inline-flex items-center gap-1 text-sm font-semibold text-brand dark:text-brand-soft">
      <ChevronLeft className="h-4 w-4" /> Homework
    </Link>
  );

  return (
    <div>
      <PageTitle title="New homework" back={back} />
      <form onSubmit={onSubmit} noValidate className="grid grid-cols-1 gap-5 md:max-w-2xl">
        <fieldset className="grid gap-2">
          <legend className="mb-2 text-sm font-semibold">Class</legend>
          <div className="flex flex-wrap gap-2">
            {divisions.map((d) => (
              <button
                key={d.name}
                type="button"
                onClick={() => {
                  setDivision(d.name);
                  setSubject("");
                  setCmap(undefined);
                }}
                aria-pressed={division === d.name}
                className={clsx(
                  "min-h-11 rounded-2xl px-4 text-[15px] font-semibold ring-1 transition",
                  division === d.name ? "bg-brand text-on-brand ring-brand" : "bg-card ring-line",
                )}
              >
                {d.student_group_name}
              </button>
            ))}
          </div>
        </fieldset>

        {form.data && form.data.suggestions.length > 0 && (
          <div className="grid gap-2">
            <p className="flex items-center gap-1.5 text-sm font-semibold">
              <Sparkles className="h-4 w-4 text-brand dark:text-brand-soft" /> From today's CMAP
            </p>
            {form.data.suggestions.map((s) => (
              <button
                key={s.cmap + s.subject}
                type="button"
                onClick={() => {
                  setSubject(s.subject || "");
                  setTitle(`${s.subject_name || s.subject || "Homework"} homework`);
                  setInstructions(plainText(s.home_work));
                  setCmap(s.cmap);
                }}
                className={clsx(
                  "rounded-2xl bg-card p-3 text-left ring-1 transition active:scale-[0.99]",
                  cmap === s.cmap ? "ring-2 ring-brand" : "ring-line",
                )}
              >
                <span className="text-xs font-bold uppercase tracking-wide text-brand dark:text-brand-soft">{s.subject_name || s.subject}</span>
                <span className="mt-0.5 line-clamp-2 block text-sm">{plainText(s.home_work)}</span>
              </button>
            ))}
          </div>
        )}

        {division && (
          <fieldset className="grid gap-2">
            <legend className="mb-2 text-sm font-semibold">Subject</legend>
            <div className="flex flex-wrap gap-2">
              {(form.data?.subjects ?? []).map((s) => (
                <button
                  key={s.name}
                  type="button"
                  onClick={() => setSubject(subject === s.name ? "" : s.name)}
                  aria-pressed={subject === s.name}
                  className={clsx(
                    "min-h-10 rounded-full px-3.5 text-sm font-semibold ring-1 transition",
                    subject === s.name ? "bg-brand-soft text-brand ring-brand dark:bg-brand/25 dark:text-brand-soft" : "bg-card text-muted ring-line",
                  )}
                >
                  {s.label}
                </button>
              ))}
              {form.isPending && <Skeleton className="h-10 w-40 rounded-full" />}
            </div>
          </fieldset>
        )}

        <label className="grid gap-1.5">
          <span className="text-sm font-semibold">Title</span>
          <input id="hw-title" value={title} onChange={(e) => setTitle(e.target.value)} className={clsx(inputCls, "h-12")} placeholder="Fractions worksheet" />
        </label>

        <label className="grid gap-1.5">
          <span className="text-sm font-semibold">Instructions</span>
          <textarea
            id="hw-instructions"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={5}
            className={clsx(inputCls, "py-3")}
            placeholder="Complete exercise 4.2, questions 1–10, in your notebook."
          />
        </label>

        <label className="grid gap-1.5">
          <span className="text-sm font-semibold">Due date</span>
          <span className="relative flex h-12 items-center gap-2 overflow-hidden rounded-2xl bg-card px-4 ring-1 ring-line">
            <CalendarDays className="h-5 w-5 text-brand dark:text-brand-soft" />
            <span className="text-base">{dueLabel(due)}</span>
            <input
              id="hw-due"
              type="date"
              value={due}
              min={localISO()}
              onChange={(e) => e.target.value && setDue(e.target.value)}
              className="absolute inset-0 h-full w-full min-w-0 cursor-pointer opacity-0"
              aria-label="Due date"
            />
          </span>
        </label>

        {error && (
          <p role="alert" className="rounded-2xl bg-bad/10 px-4 py-3 text-sm font-medium text-bad">
            {error}
          </p>
        )}

        <Button type="submit" loading={create.isPending} className="w-full md:w-auto md:justify-self-start">
          Set homework
        </Button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------- detail

const STATES: { value: HomeworkStatus; label: string; icon: typeof Check; cls: string }[] = [
  { value: "Pending", label: "Not yet", icon: CircleDashed, cls: "bg-line/80 text-ink" },
  { value: "Submitted", label: "Handed in", icon: Check, cls: "bg-good text-white" },
  { value: "Reviewed", label: "Checked", icon: Star, cls: "bg-brand text-on-brand" },
];

export function HomeworkDetail() {
  const { name = "" } = useParams();
  const { data: hw, isPending, error, refetch } = useHomework(name);
  const update = useUpdateHomework(name);
  const [statuses, setStatuses] = useState<Record<string, HomeworkStatus>>({});
  const [remarks, setRemarks] = useState<Record<string, string>>({});
  const [openRemark, setOpenRemark] = useState<string | null>(null);
  const [toast, setToast] = useState("");

  const saved = useMemo(() => {
    const s: Record<string, HomeworkStatus> = {};
    const r: Record<string, string> = {};
    for (const row of hw?.submissions ?? []) {
      s[row.student] = row.status;
      r[row.student] = row.remarks || "";
    }
    return { s, r };
  }, [hw]);
  useEffect(() => {
    setStatuses(saved.s);
    setRemarks(saved.r);
  }, [saved]);
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(""), 3000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const changed = Object.keys(saved.s).filter((st) => statuses[st] !== saved.s[st] || (remarks[st] ?? "") !== (saved.r[st] ?? ""));

  async function saveChanges(status?: "Open" | "Closed") {
    const updates = Object.fromEntries(changed.map((st) => [st, { status: statuses[st], remarks: remarks[st] }]));
    try {
      await update.mutateAsync({ updates, status });
      setToast(status === "Closed" ? "Homework closed" : status === "Open" ? "Homework reopened" : "Saved");
    } catch (e) {
      setToast((e as Error).message);
    }
  }

  const back = (
    <Link to="/homework" className="mb-1 inline-flex items-center gap-1 text-sm font-semibold text-brand dark:text-brand-soft">
      <ChevronLeft className="h-4 w-4" /> Homework
    </Link>
  );

  if (isPending)
    return (
      <div className="grid grid-cols-1 gap-4">
        <PageTitle title="Homework" back={back} />
        <Skeleton className="h-32" />
        <Skeleton className="h-96" />
      </div>
    );
  if (error)
    return (
      <div>
        <PageTitle title="Homework" back={back} />
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      </div>
    );

  const handedIn = Object.values(statuses).filter((s) => s !== "Pending").length;
  const text = plainText(hw.instructions);

  return (
    <div className="pb-28 md:pb-24">
      <PageTitle title={hw.title} subtitle={`${hw.division_name} · ${dueLabel(hw.due_date)}`} back={back} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5 lg:items-start">
        <Card className="grid gap-3 lg:col-span-2">
          <div className="flex flex-wrap gap-1.5">
            {hw.subject_name && <Chip>{hw.subject_name}</Chip>}
            <Chip tone="muted">Set {formatDay(hw.assigned_on)}</Chip>
            {hw.status === "Closed" && <Chip tone="muted">Closed</Chip>}
          </div>
          {text ? <p className="whitespace-pre-line text-[15px]">{text}</p> : <p className="text-sm text-muted">No instructions added.</p>}
          <div className="flex items-center gap-3 border-t border-line pt-3">
            <span className="tabular text-2xl font-extrabold text-good">{handedIn}</span>
            <span className="text-sm text-muted">of {hw.total} handed in</span>
            <button
              type="button"
              onClick={() => saveChanges(hw.status === "Open" ? "Closed" : "Open")}
              className="ml-auto text-sm font-semibold text-brand dark:text-brand-soft"
            >
              {hw.status === "Open" ? "Close homework" : "Reopen"}
            </button>
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-3 lg:col-span-3">
          <div className="flex items-center justify-between px-1">
            <p className="text-sm text-muted">Tap to record who handed it in.</p>
            <button
              type="button"
              onClick={() => setStatuses((s) => Object.fromEntries(Object.entries(s).map(([k, v]) => [k, v === "Pending" ? "Submitted" : v])))}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-good/10 px-3 py-2 text-sm font-bold text-good active:scale-95"
            >
              <CheckCheck className="h-4 w-4" /> Rest handed in
            </button>
          </div>
          <Card flush className="overflow-hidden">
            <ul className="divide-y divide-line">
              {hw.submissions.map((row) => (
                <li key={row.student} className="px-3 py-2.5 sm:px-4">
                  <div className="flex items-center gap-3">
                    <span className="tabular w-6 shrink-0 text-right text-sm font-bold text-muted">{row.roll_no}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[15px] font-semibold">{row.student_name}</span>
                      {remarks[row.student] && openRemark !== row.student && (
                        <span className="block truncate text-xs text-muted">“{remarks[row.student]}”</span>
                      )}
                    </span>
                    <button
                      type="button"
                      onClick={() => setOpenRemark(openRemark === row.student ? null : row.student)}
                      aria-label={`Remark for ${row.student_name}`}
                      aria-expanded={openRemark === row.student}
                      className={clsx("grid h-10 w-9 shrink-0 place-items-center rounded-xl", remarks[row.student] ? "text-brand dark:text-brand-soft" : "text-muted")}
                    >
                      <MessageSquareText className="h-5 w-5" />
                    </button>
                    <div role="radiogroup" aria-label={`Homework for ${row.student_name}`} className="flex shrink-0 gap-1">
                      {STATES.map(({ value, label, icon: Icon, cls }) => (
                        <button
                          key={value}
                          type="button"
                          role="radio"
                          aria-checked={statuses[row.student] === value}
                          aria-label={label}
                          title={label}
                          onClick={() => setStatuses((s) => ({ ...s, [row.student]: value }))}
                          className={clsx(
                            "grid h-10 w-10 place-items-center rounded-xl transition active:scale-90",
                            statuses[row.student] === value ? cls : "bg-bg text-muted ring-1 ring-line",
                          )}
                        >
                          <Icon className="h-[18px] w-[18px]" />
                        </button>
                      ))}
                    </div>
                  </div>
                  {openRemark === row.student && (
                    <input
                      id={`remark-${row.student}`}
                      autoFocus
                      value={remarks[row.student] ?? ""}
                      onChange={(e) => setRemarks((r) => ({ ...r, [row.student]: e.target.value }))}
                      placeholder="Add a remark, e.g. Neat work"
                      className={clsx(inputCls, "mt-2 h-11")}
                    />
                  )}
                </li>
              ))}
            </ul>
          </Card>
          <p className="px-1 text-xs text-muted">
            <CircleDashed className="inline h-3.5 w-3.5" /> Not yet · <Check className="inline h-3.5 w-3.5" /> Handed in ·{" "}
            <Star className="inline h-3.5 w-3.5" /> Checked
          </p>
        </div>
      </div>

      {changed.length > 0 && (
        <div className="fixed inset-x-0 bottom-[calc(64px+env(safe-area-inset-bottom,0px))] z-10 border-t border-line/80 bg-card/90 px-4 py-3 backdrop-blur-xl md:bottom-0 md:left-64 md:px-8">
          <div className="mx-auto flex max-w-xl items-center gap-3 md:max-w-3xl lg:max-w-5xl">
            <p className="flex-1 text-sm text-muted">
              {changed.length} change{changed.length > 1 ? "s" : ""} not saved
            </p>
            <Button onClick={() => saveChanges()} loading={update.isPending}>
              Save
            </Button>
          </div>
        </div>
      )}

      {toast && (
        <div role="status" className="fixed inset-x-4 bottom-[calc(140px+env(safe-area-inset-bottom,0px))] z-40 mx-auto max-w-sm rounded-2xl bg-ink px-4 py-3 text-center text-sm font-semibold text-bg shadow-float md:bottom-24">
          {toast}
        </div>
      )}
    </div>
  );
}
