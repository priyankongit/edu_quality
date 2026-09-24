import clsx from "clsx";
import { CalendarDays, CheckCheck, CheckCircle2, ChevronLeft, Lock, PartyPopper, UsersRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { Avatar, Button, Card, EmptyState, Skeleton } from "@/components/ui";
import { formatDay, isToday, localISO } from "@/lib/dates";
import { useRegister, useSaveRegister } from "@/lib/queries";
import type { AttendanceStatus, Register } from "@/lib/types";

const FALLBACK_COLOR = { Present: "#16A34A", Absent: "#DC2626", Other: "#2563EB" } as const;
const colorOf = (s: AttendanceStatus) => s.color || FALLBACK_COLOR[s.type] || "#6B7280";

function StatusButtons({
  statuses,
  value,
  onChange,
  studentName,
}: {
  statuses: AttendanceStatus[];
  value?: string;
  onChange: (status: string) => void;
  studentName: string;
}) {
  return (
    <div role="radiogroup" aria-label={`Attendance for ${studentName}`} className="flex shrink-0 gap-1.5">
      {statuses.map((s) => {
        const selected = value === s.name;
        return (
          <button
            key={s.name}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={s.name}
            title={s.name}
            onClick={() => onChange(s.name)}
            className={clsx(
              "grid h-10 w-10 place-items-center rounded-xl text-sm font-extrabold transition active:scale-90",
              selected ? "text-white shadow-sm" : "bg-bg text-muted ring-1 ring-line",
            )}
            style={selected ? { backgroundColor: colorOf(s) } : undefined}
          >
            {s.code || s.name[0]}
          </button>
        );
      })}
    </div>
  );
}

function Counts({ register, marks }: { register: Register; marks: Record<string, string> }) {
  const types = Object.fromEntries(register.statuses.map((s) => [s.name, s.type]));
  const values = register.students.map((s) => marks[s.student]).filter(Boolean);
  const absent = values.filter((v) => types[v] === "Absent").length;
  const present = values.length - absent;
  const unmarked = register.students.length - values.length;
  const cells = [
    { label: "Present", value: present, cls: "text-good" },
    { label: "Absent", value: absent, cls: "text-bad" },
    { label: "Unmarked", value: unmarked, cls: unmarked ? "text-warn" : "text-muted" },
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

function ConfirmSubmit({
  register,
  marks,
  busy,
  onCancel,
  onConfirm,
}: {
  register: Register;
  marks: Record<string, string>;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const types = Object.fromEntries(register.statuses.map((s) => [s.name, s.type]));
  const absent = register.students.filter((s) => types[marks[s.student]] === "Absent");
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 md:items-center" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="pb-safe w-full max-w-md rounded-t-4xl bg-card p-6 shadow-float md:rounded-4xl">
        <h2 id="confirm-title" className="text-xl font-extrabold tracking-tight">
          Submit {register.division.student_group_name}?
        </h2>
        <p className="mt-1 text-[15px] text-muted">{formatDay(register.date, { weekday: "long", day: "numeric", month: "long" })}</p>
        <div className="mt-4 grid gap-2 rounded-2xl bg-bg p-4 text-[15px]">
          <p>
            <b className="tabular">{register.students.length - absent.length}</b> in school,{" "}
            <b className="tabular">{absent.length}</b> absent.
          </p>
          {absent.length > 0 && (
            <p className="text-sm text-muted">
              Absent: {absent.map((s) => s.student_name).join(", ")}. Their parents get an alert if the school has it switched on.
            </p>
          )}
          <p className="text-sm text-muted">Once submitted, this register can only be changed by the school office.</p>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Keep editing
          </Button>
          <Button onClick={onConfirm} loading={busy}>
            Submit
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function Attendance() {
  const { division = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const date = params.get("date") || localISO();
  const { data: register, isPending, error, refetch } = useRegister(division, date);
  const save = useSaveRegister(division, date);

  const [marks, setMarks] = useState<Record<string, string>>({});
  const [confirming, setConfirming] = useState(false);
  const [toast, setToast] = useState("");

  const saved = useMemo(
    () => Object.fromEntries((register?.students ?? []).filter((s) => s.status).map((s) => [s.student, s.status as string])),
    [register],
  );
  useEffect(() => setMarks(saved), [saved]);
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  const editable = register?.students.filter((s) => !s.locked) ?? [];
  const dirty = editable.some((s) => marks[s.student] !== saved[s.student]);
  const allMarked = !!register && register.students.every((s) => marks[s.student]);
  const presentStatus = register?.statuses.find((s) => s.name === "Present") ?? register?.statuses.find((s) => s.type === "Present");

  function mark(student: string, status: string) {
    setMarks((m) => ({ ...m, [student]: status }));
  }

  function markRestPresent() {
    if (!presentStatus || !register) return;
    setMarks((m) => {
      const next = { ...m };
      for (const s of editable) if (!next[s.student]) next[s.student] = presentStatus.name;
      return next;
    });
  }

  function changedMarks() {
    return Object.fromEntries(editable.filter((s) => marks[s.student]).map((s) => [s.student, marks[s.student]]));
  }

  async function saveDraft() {
    try {
      await save.mutateAsync({ marks: changedMarks(), submit: false });
      setToast("Draft saved");
    } catch (e) {
      setToast((e as Error).message);
    }
  }

  async function submit() {
    try {
      const res = await save.mutateAsync({ marks: changedMarks(), submit: true });
      setConfirming(false);
      setToast(res.notified ? `Submitted · ${res.notified} absence alert${res.notified > 1 ? "s" : ""} queued` : "Attendance submitted");
    } catch (e) {
      setConfirming(false);
      setToast((e as Error).message);
    }
  }

  const back = (
    <Link to="/" className="mb-1 inline-flex items-center gap-1 text-sm font-semibold text-brand dark:text-brand-soft">
      <ChevronLeft className="h-4 w-4" /> Today
    </Link>
  );

  const datePicker = (
    <label className="relative inline-flex h-11 shrink-0 items-center gap-2 overflow-hidden rounded-2xl bg-card px-3.5 text-sm font-semibold shadow-card ring-1 ring-line/60">
      <CalendarDays className="h-4 w-4 text-brand dark:text-brand-soft" />
      {isToday(date) ? "Today" : formatDay(date)}
      <input
        id="register-date"
        type="date"
        value={date}
        max={localISO()}
        onChange={(e) => e.target.value && setParams({ date: e.target.value }, { replace: true })}
        // Date inputs keep an intrinsic ~150px width even with inset-0; pin the size or it
        // overflows the chip and widens the whole page on phones.
        className="absolute inset-0 h-full w-full min-w-0 cursor-pointer opacity-0"
        aria-label="Attendance date"
      />
    </label>
  );

  if (isPending) {
    return (
      <div className="grid grid-cols-1 gap-4">
        <PageTitle title="Attendance" back={back} />
        <Skeleton className="h-20" />
        <Skeleton className="h-96" />
      </div>
    );
  }
  if (error) {
    return (
      <div>
        <PageTitle title="Attendance" back={back} action={datePicker} />
        <Card className="text-sm">
          <p className="font-semibold text-bad">{error.message}</p>
          <button type="button" onClick={() => refetch()} className="mt-2 font-semibold text-brand dark:text-brand-soft">
            Try again
          </button>
        </Card>
      </div>
    );
  }

  const r = register;
  return (
    <div className="pb-28 md:pb-24">
      <PageTitle title={r.division.student_group_name} subtitle={formatDay(r.date, { weekday: "long", day: "numeric", month: "long" })} back={back} action={datePicker} />

      {/* grid-cols-1 = minmax(0, 1fr): without it the column grows to the counters' preferred width on phones. */}
      <div className="grid grid-cols-1 gap-4">
        {r.holiday && (
          <Card className="flex items-center gap-3 bg-warn/10 text-sm font-semibold text-warn ring-warn/20">
            <PartyPopper className="h-5 w-5 shrink-0" /> The school calendar marks this day as a holiday for this class.
          </Card>
        )}
        {r.submitted && (
          <Card className="flex items-center gap-3 bg-good/10 text-sm font-semibold text-good ring-good/20">
            <CheckCircle2 className="h-5 w-5 shrink-0" /> Submitted. Ask the school office if anything needs correcting.
          </Card>
        )}

        {r.students.length === 0 ? (
          <EmptyState icon={<UsersRound className="h-7 w-7" />} title="No students in this division">
            Students appear here once they're enrolled in {r.division.student_group_name}.
          </EmptyState>
        ) : (
          <>
            <Counts register={r} marks={marks} />

            {!r.submitted && presentStatus && (
              <div className="flex items-center justify-between gap-3 px-1">
                <p className="text-sm text-muted">
                  {r.statuses.map((s) => `${s.code} ${s.name}`).join(" · ")}
                </p>
                <button
                  type="button"
                  onClick={markRestPresent}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-good/10 px-3 py-2 text-sm font-bold text-good active:scale-95"
                >
                  <CheckCheck className="h-4 w-4" /> Rest present
                </button>
              </div>
            )}

            <Card flush className="overflow-hidden">
              <ul className="divide-y divide-line lg:grid lg:grid-cols-2 lg:divide-y-0">
                {r.students.map((s) => {
                  const status = r.statuses.find((x) => x.name === marks[s.student]);
                  return (
                    <li key={s.student} className="flex items-center gap-3 px-3 py-2.5 sm:px-4 lg:border-b lg:border-line lg:odd:border-r">
                      <span className="tabular w-6 shrink-0 text-right text-sm font-bold text-muted">{s.roll_no}</span>
                      <span className="hidden min-[400px]:block">
                        <Avatar name={s.student_name} image={s.image} size={36} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[15px] font-semibold">{s.student_name}</span>
                        <span className="block truncate text-xs font-semibold" style={{ color: status ? colorOf(status) : undefined }}>
                          {status ? status.name : <span className="text-muted">Not marked</span>}
                        </span>
                      </span>
                      {s.locked ? (
                        <Lock className="h-4 w-4 shrink-0 text-muted" aria-label="Submitted" />
                      ) : (
                        <StatusButtons statuses={r.statuses} value={marks[s.student]} onChange={(v) => mark(s.student, v)} studentName={s.student_name} />
                      )}
                    </li>
                  );
                })}
              </ul>
            </Card>
          </>
        )}
      </div>

      {!r.submitted && r.students.length > 0 && (
        <div className="fixed inset-x-0 bottom-[calc(64px+env(safe-area-inset-bottom,0px))] z-10 border-t border-line/80 bg-card/90 px-4 py-3 backdrop-blur-xl md:bottom-0 md:left-64 md:px-8">
          <div className="mx-auto flex max-w-xl items-center gap-3 md:max-w-3xl lg:max-w-5xl">
            <p className="hidden flex-1 text-sm text-muted sm:block">
              {allMarked ? "Everyone is marked." : "Mark every student to submit."}
            </p>
            <Button variant="ghost" onClick={saveDraft} disabled={!dirty} loading={save.isPending && !confirming} className="flex-1 sm:flex-none">
              Save draft
            </Button>
            <Button onClick={() => setConfirming(true)} disabled={!allMarked || save.isPending} className="flex-1 sm:flex-none">
              Submit
            </Button>
          </div>
        </div>
      )}

      {confirming && (
        <ConfirmSubmit register={r} marks={marks} busy={save.isPending} onCancel={() => setConfirming(false)} onConfirm={submit} />
      )}

      {toast && (
        <div
          role="status"
          className="fixed inset-x-4 bottom-[calc(140px+env(safe-area-inset-bottom,0px))] z-40 mx-auto max-w-sm rounded-2xl bg-ink px-4 py-3 text-center text-sm font-semibold text-bg shadow-float md:bottom-24"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
