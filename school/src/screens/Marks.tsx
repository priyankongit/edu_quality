import clsx from "clsx";
import { ChevronLeft, ChevronRight, ClipboardList, Lock } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Link, useBlocker, useParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { Button, Card, Chip, EmptyState, SectionTitle, Skeleton } from "@/components/ui";
import { formatDay } from "@/lib/dates";
import { useExamList, useMarksSheet, useSaveMarks } from "@/lib/queries";
import type { ExamSummary, MarksSheet as Sheet } from "@/lib/types";

const ABSENT = "-";

function examTitle(e: ExamSummary) {
  return e.subject_name || e.subject || e.assessment_name;
}

function examMeta(e: ExamSummary) {
  const when = e.schedule_date ? formatDay(e.schedule_date) : "No date set";
  return `${when} · ${e.scoring_type === "Grades" ? "Graded" : `Out of ${e.maximum_score}`}`;
}

const published = (e: ExamSummary) => e.strength > 0 && e.submitted >= e.strength;

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

function ExamCard({ exam }: { exam: ExamSummary }) {
  const pct = exam.strength ? Math.min(100, Math.round((exam.entered / exam.strength) * 100)) : 0;
  return (
    <Link
      to={`/marks/${encodeURIComponent(exam.name)}`}
      className="group grid gap-3 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            <Chip>{exam.assessment_group_name || exam.assessment_group}</Chip>
            <Chip tone="muted">{exam.division_name}</Chip>
            {exam.mine && <Chip tone="muted">Yours</Chip>}
            {published(exam) && <Chip tone="muted">Published</Chip>}
          </div>
          <p className="truncate text-[16px] font-bold">{examTitle(exam)}</p>
          <p className="text-sm text-muted">{examMeta(exam)}</p>
        </div>
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted transition group-hover:translate-x-0.5" />
      </div>
      <div className="flex items-center gap-3">
        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line" aria-hidden>
          <span className="block h-full rounded-full bg-good" style={{ width: `${pct}%` }} />
        </span>
        <span className="tabular shrink-0 text-xs font-semibold text-muted">
          {Math.min(exam.entered, exam.strength)}/{exam.strength} marked
        </span>
      </div>
    </Link>
  );
}

export function MarksList() {
  const { data, isPending, error, refetch } = useExamList();
  const [division, setDivision] = useState("");

  const divisions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const e of data ?? []) seen.set(e.division, e.division_name);
    return [...seen].sort((a, b) => a[1].localeCompare(b[1]));
  }, [data]);
  const shown = (data ?? []).filter((e) => !division || e.division === division);
  const open = shown.filter((e) => !published(e) && e.entered < e.strength).sort((a, b) => Number(b.mine) - Number(a.mine));
  const done = shown.filter((e) => !open.includes(e));

  return (
    <div>
      <PageTitle title="Marks" subtitle="Enter exam marks for your classes" />
      {isPending ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.length === 0 ? (
        <EmptyState icon={<ClipboardList className="h-7 w-7" />} title="No exams to mark">
          Exams show up here once the exam office sets them up for your classes.
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {divisions.length > 1 && (
            <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:px-0">
              {[["", "All classes"], ...divisions].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setDivision(value)}
                  aria-pressed={division === value}
                  className={clsx(
                    "min-h-10 shrink-0 rounded-full px-3.5 text-sm font-semibold ring-1 transition",
                    division === value ? "bg-brand text-on-brand ring-brand" : "bg-card text-muted ring-line",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          {open.length > 0 && (
            <section className="grid grid-cols-1 gap-3">
              <SectionTitle>To finish</SectionTitle>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {open.map((e) => (
                  <ExamCard key={e.name} exam={e} />
                ))}
              </div>
            </section>
          )}
          {done.length > 0 && (
            <section className="grid grid-cols-1 gap-3">
              <SectionTitle>Marked</SectionTitle>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {done.map((e) => (
                  <ExamCard key={e.name} exam={e} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- sheet

type Values = Record<string, Record<string, string>>;

function problemWith(value: string, scoring: Sheet["scoring_type"], maximum: number, grades: Set<string>) {
  if (value === "" || value === ABSENT) return "";
  if (scoring === "Grades") return grades.has(value.toUpperCase()) ? "" : "Not a grade on this scale";
  if (!/^\d+(\.\d+)?$/.test(value)) return "Enter a number, or AB for absent";
  if (Number(value) > maximum) return `More than ${maximum}`;
  return "";
}

/** Typing "ab" or "-" marks absent; typing over "AB" starts a fresh mark. */
function nextMarkValue(previous: string, raw: string) {
  const up = raw.trim().toUpperCase();
  if (up === "AB" || up === ABSENT) return ABSENT;
  if (previous === ABSENT) return up === "A" ? "" : up.replace(/^AB/, "");
  return up;
}

function Stats({ sheet, values }: { sheet: Sheet; values: Values }) {
  const rows = sheet.students.map((s) => sheet.criteria.map((c) => values[s.student]?.[c.name] ?? ""));
  const entered = rows.filter((r) => r.some((v) => v !== "")).length;
  const absent = rows.filter((r) => r.length > 0 && r.every((v) => v === ABSENT)).length;
  const totals = rows.filter((r) => r.every((v) => v !== "" && v !== ABSENT && !Number.isNaN(Number(v)))).map((r) => r.reduce((a, v) => a + Number(v), 0));
  const cells = [
    { label: "Marked", value: `${entered}/${sheet.students.length}`, cls: entered < sheet.students.length ? "text-warn" : "text-good" },
    { label: "Absent", value: String(absent), cls: absent ? "text-bad" : "text-muted" },
    sheet.scoring_type === "Marks"
      ? { label: `Average /${sheet.maximum_score}`, value: totals.length ? (totals.reduce((a, b) => a + b, 0) / totals.length).toFixed(1) : "–", cls: "text-ink" }
      : { label: "Graded", value: String(rows.filter((r) => r.length > 0 && r.every((v) => v !== "" && v !== ABSENT)).length), cls: "text-ink" },
  ];
  return (
    <div className="grid grid-cols-3 gap-2">
      {cells.map((c) => (
        <Card key={c.label} className="grid gap-0.5 px-3 py-3 text-center">
          <span className={clsx("tabular text-2xl font-extrabold", c.cls)}>{c.value}</span>
          <span className="text-xs font-semibold text-muted">{c.label}</span>
        </Card>
      ))}
    </div>
  );
}

export function MarksSheet() {
  const { plan = "" } = useParams();
  const { data: sheet, isPending, error, refetch } = useMarksSheet(plan);
  const save = useSaveMarks(plan);
  const [values, setValues] = useState<Values>({});
  const [toast, setToast] = useState("");
  const cells = useRef(new Map<string, HTMLInputElement | HTMLSelectElement>());

  const saved = useMemo(() => {
    const v: Values = {};
    for (const s of sheet?.students ?? []) {
      v[s.student] = Object.fromEntries((sheet?.criteria ?? []).map((c) => [c.name, s.values[c.name] == null ? "" : String(s.values[c.name])]));
    }
    return v;
  }, [sheet]);
  useEffect(() => setValues(saved), [saved]);
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  const grades = useMemo(() => new Set((sheet?.grades ?? []).map((g) => g.code.toUpperCase())), [sheet]);
  const changes = useMemo(() => {
    const out: Values = {};
    for (const [student, row] of Object.entries(values)) {
      for (const [criteria, value] of Object.entries(row)) {
        if (value !== (saved[student]?.[criteria] ?? "")) (out[student] ??= {})[criteria] = value;
      }
    }
    return out;
  }, [values, saved]);
  const changed = Object.keys(changes).length;
  const problems = useMemo(() => {
    if (!sheet) return new Map<string, string>();
    const out = new Map<string, string>();
    for (const s of sheet.students) {
      for (const c of sheet.criteria) {
        const p = problemWith(values[s.student]?.[c.name] ?? "", sheet.scoring_type, c.maximum_score, grades);
        if (p) out.set(`${s.student}|${c.name}`, p);
      }
    }
    return out;
  }, [sheet, values, grades]);

  // Don't lose typed marks to a stray tap on the tab bar or a closed tab.
  const blocker = useBlocker(({ currentLocation, nextLocation }) => changed > 0 && currentLocation.pathname !== nextLocation.pathname);
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (window.confirm("You have marks that aren't saved. Leave anyway?")) blocker.proceed();
    else blocker.reset();
  }, [blocker]);
  useEffect(() => {
    if (!changed) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [changed]);

  function setValue(student: string, criteria: string, value: string) {
    setValues((v) => ({ ...v, [student]: { ...v[student], [criteria]: value } }));
  }

  function toggleAbsent(student: string) {
    if (!sheet) return;
    const allAbsent = sheet.criteria.every((c) => values[student]?.[c.name] === ABSENT);
    setValues((v) => ({ ...v, [student]: Object.fromEntries(sheet.criteria.map((c) => [c.name, allAbsent ? "" : ABSENT])) }));
  }

  /** Enter moves down the column, like a paper mark sheet. */
  function onKeyDown(e: KeyboardEvent, row: number, col: number) {
    if (e.key !== "Enter" || !sheet) return;
    e.preventDefault();
    for (let r = row + 1; r < sheet.students.length; r++) {
      const next = cells.current.get(`${r}|${col}`);
      if (next && !next.disabled) return next.focus();
    }
    (e.target as HTMLElement).blur();
  }

  async function onSave() {
    if (problems.size) {
      setToast(`Fix ${problems.size} highlighted mark${problems.size > 1 ? "s" : ""} first`);
      return;
    }
    try {
      const res = await save.mutateAsync(changes);
      setToast(res.skipped ? `Saved. ${res.skipped} already published by the exam office were left as they were.` : "Marks saved");
    } catch (e) {
      setToast((e as Error).message);
    }
  }

  const back = (
    <Link to="/marks" className="mb-1 inline-flex items-center gap-1 text-sm font-semibold text-brand dark:text-brand-soft">
      <ChevronLeft className="h-4 w-4" /> Marks
    </Link>
  );

  if (isPending)
    return (
      <div className="grid grid-cols-1 gap-4">
        <PageTitle title="Marks" back={back} />
        <Skeleton className="h-24" />
        <Skeleton className="h-96" />
      </div>
    );
  if (error)
    return (
      <div>
        <PageTitle title="Marks" back={back} />
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      </div>
    );

  const multi = sheet.criteria.length > 1;
  const inputCls = "h-11 w-[4.25rem] rounded-xl bg-bg text-center text-base font-bold tabular ring-1 ring-line focus:bg-card focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-60";

  return (
    <div className="pb-28 md:pb-24">
      <PageTitle title={examTitle(sheet)} subtitle={`${sheet.division_name} · ${examMeta(sheet)}`} back={back} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5 lg:items-start">
        <div className="grid grid-cols-1 gap-3 lg:col-span-2">
          <Card className="grid gap-3">
            <div className="flex flex-wrap gap-1.5">
              <Chip>{sheet.assessment_group_name || sheet.assessment_group}</Chip>
              {sheet.exam_type && <Chip tone="muted">{sheet.exam_type}</Chip>}
              {published(sheet) && <Chip tone="muted">Published</Chip>}
            </div>
            {multi && (
              <ul className="grid gap-1 text-sm">
                {sheet.criteria.map((c) => (
                  <li key={c.name} className="flex justify-between gap-3">
                    <span className="text-muted">{c.name}</span>
                    {sheet.scoring_type === "Marks" && <span className="tabular font-semibold">{c.maximum_score}</span>}
                  </li>
                ))}
              </ul>
            )}
            <p className="border-t border-line pt-3 text-xs text-muted">
              Marks are saved as a draft. The exam office publishes results, and after that they can't be changed here.
            </p>
          </Card>
          <Stats sheet={sheet} values={values} />
        </div>

        <div className="grid grid-cols-1 gap-3 lg:col-span-3">
          <p className="px-1 text-sm text-muted">
            {sheet.scoring_type === "Marks" ? "Type each mark and press Enter for the next student. Tap AB if absent." : "Pick a grade for each student. Tap AB if absent."}
          </p>
          <Card flush className="overflow-hidden">
            {multi && (
              <div className="flex items-center gap-2 border-b border-line bg-bg/60 px-3 py-2 sm:px-4">
                <span className="flex-1 text-xs font-semibold uppercase tracking-wide text-muted">Student</span>
                {sheet.criteria.map((c) => (
                  <span key={c.name} className="w-[4.25rem] truncate text-center text-[11px] font-bold text-muted" title={c.name}>
                    {c.name}
                  </span>
                ))}
                <span className="w-11" />
              </div>
            )}
            <ul className="divide-y divide-line">
              {sheet.students.map((s, row) => {
                const rowValues = values[s.student] ?? {};
                const absent = sheet.criteria.every((c) => rowValues[c.name] === ABSENT);
                const nums = sheet.criteria.map((c) => rowValues[c.name]).filter((v) => v && v !== ABSENT && !Number.isNaN(Number(v)));
                const rowProblem = sheet.criteria.map((c) => problems.get(`${s.student}|${c.name}`)).find(Boolean);
                return (
                  <li key={s.student} className={clsx("px-3 py-2 sm:px-4", s.locked && "bg-bg/50")}>
                    <div className="flex items-center gap-2">
                      <span className="tabular w-6 shrink-0 text-right text-sm font-bold text-muted">{s.roll_no}</span>
                      <span className="min-w-0 flex-1 pl-1">
                        <span className="block truncate text-[15px] font-semibold">{s.student_name}</span>
                        {rowProblem ? (
                          <span className="block truncate text-xs font-semibold text-bad">{rowProblem}</span>
                        ) : multi && sheet.scoring_type === "Marks" && nums.length > 0 ? (
                          <span className="tabular block text-xs text-muted">
                            Total {nums.reduce((a, v) => a + Number(v), 0)}/{sheet.maximum_score}
                          </span>
                        ) : null}
                      </span>
                      {sheet.criteria.map((c, col) => {
                        const value = rowValues[c.name] ?? "";
                        const bad = problems.has(`${s.student}|${c.name}`);
                        const label = `${c.name} for ${s.student_name}`;
                        const ref = (el: HTMLInputElement | HTMLSelectElement | null) => {
                          if (el) cells.current.set(`${row}|${col}`, el);
                          else cells.current.delete(`${row}|${col}`);
                        };
                        return sheet.scoring_type === "Grades" ? (
                          <select
                            key={c.name}
                            ref={ref}
                            aria-label={label}
                            value={value}
                            disabled={s.locked}
                            onChange={(e) => setValue(s.student, c.name, e.target.value)}
                            className={clsx(inputCls, "appearance-none px-1", bad && "ring-2 ring-bad", value === ABSENT && "text-bad")}
                          >
                            <option value="">–</option>
                            {sheet.grades.map((g) => (
                              <option key={g.code} value={g.code}>
                                {g.code}
                              </option>
                            ))}
                            <option value={ABSENT}>AB</option>
                          </select>
                        ) : (
                          <input
                            key={c.name}
                            ref={ref}
                            aria-label={label}
                            aria-invalid={bad}
                            inputMode="decimal"
                            enterKeyHint="next"
                            autoComplete="off"
                            placeholder="–"
                            value={value === ABSENT ? "AB" : value}
                            disabled={s.locked}
                            onChange={(e) => setValue(s.student, c.name, nextMarkValue(value, e.target.value))}
                            onKeyDown={(e) => onKeyDown(e, row, col)}
                            onFocus={(e) => e.target.select()}
                            className={clsx(inputCls, bad && "ring-2 ring-bad", value === ABSENT && "text-bad")}
                          />
                        );
                      })}
                      {s.locked ? (
                        <span className="grid h-11 w-11 shrink-0 place-items-center text-muted" title="Published by the exam office">
                          <Lock className="h-4 w-4" aria-label="Published" />
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => toggleAbsent(s.student)}
                          aria-pressed={absent}
                          aria-label={`Mark ${s.student_name} absent`}
                          className={clsx(
                            "grid h-11 w-11 shrink-0 place-items-center rounded-xl text-xs font-extrabold transition active:scale-90",
                            absent ? "bg-bad text-white" : "bg-bg text-muted ring-1 ring-line",
                          )}
                        >
                          AB
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </div>
      </div>

      {changed > 0 && (
        <div className="fixed inset-x-0 bottom-[calc(64px+env(safe-area-inset-bottom,0px))] z-10 border-t border-line/80 bg-card/90 px-4 py-3 backdrop-blur-xl md:bottom-0 md:left-64 md:px-8">
          <div className="mx-auto flex max-w-xl items-center gap-3 md:max-w-3xl lg:max-w-5xl">
            <p className="flex-1 text-sm text-muted">
              {changed} student{changed > 1 ? "s" : ""} changed
              {problems.size > 0 && <span className="font-semibold text-bad"> · {problems.size} to fix</span>}
            </p>
            <Button onClick={onSave} loading={save.isPending}>
              Save marks
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
