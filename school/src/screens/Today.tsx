import clsx from "clsx";
import { CalendarClock, ClipboardCheck, GraduationCap, NotebookPen, PenLine, UsersRound } from "lucide-react";
import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import DivisionCard, { registerPath } from "@/components/DivisionCard";
import { Card, Chip, EmptyState, SectionTitle, Skeleton } from "@/components/ui";
import { minutesOf } from "@/lib/dates";
import { useBrand, useCurrentUser, useMyDay } from "@/lib/queries";
import type { MyDay, Period } from "@/lib/types";

function greeting(date: Date) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function Hero({ day }: { day?: MyDay }) {
  const brand = useBrand();
  const user = useCurrentUser();
  const firstName = (user.instructor?.instructor_name || user.full_name || "").split(" ")[0];
  const open = day?.divisions.filter((d) => !d.holiday) ?? [];
  const done = open.filter((d) => d.attendance.submitted).length;

  return (
    <section className="relative overflow-hidden rounded-4xl bg-brand p-5 text-on-brand shadow-float shadow-brand/30 md:p-6">
      <div aria-hidden className="absolute -right-10 -top-12 h-44 w-44 rounded-full bg-white/10" />
      <div aria-hidden className="absolute -bottom-16 right-16 h-32 w-32 rounded-full bg-white/10" />
      <p className="relative text-sm font-semibold opacity-80">{greeting(new Date())},</p>
      <p className="relative text-[26px] font-extrabold leading-tight tracking-tight md:text-3xl">{firstName || "Teacher"}</p>
      <p className="relative mt-1 text-sm opacity-85">{user.instructor?.school || brand.school_name}</p>
      {day && open.length > 0 && (
        <div className="relative mt-5 flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/25">
            <div className="h-full rounded-full bg-white transition-all" style={{ width: `${(done / open.length) * 100}%` }} />
          </div>
          <p className="tabular text-sm font-bold">
            {done}/{open.length} registers done
          </p>
        </div>
      )}
    </section>
  );
}

function Timetable({ periods }: { periods: Period[] }) {
  const now = new Date();
  const mins = now.getHours() * 60 + now.getMinutes();
  return (
    <Card flush className="p-2">
      <ol className="grid">
        {periods.map((p) => {
          const current = mins >= minutesOf(p.from_time) && mins < minutesOf(p.to_time);
          const past = mins >= minutesOf(p.to_time);
          return (
            <li
              key={p.name}
              className={clsx(
                "flex items-center gap-3 rounded-2xl px-3 py-2.5",
                current && "bg-brand-soft dark:bg-brand/25",
                past && "opacity-55",
              )}
            >
              <span className="tabular w-[92px] shrink-0 text-sm font-semibold text-muted">
                {p.from_time}–{p.to_time}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[15px] font-bold">{p.subject_name || p.subject}</span>
                <span className="block truncate text-xs text-muted">{p.division_name}</span>
              </span>
              {current && <Chip>Now</Chip>}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

type Action = { label: string; hint: string; icon: ComponentType<{ className?: string }>; to?: string };

function QuickActions({ day }: { day?: MyDay }) {
  const pending = day?.divisions.find((d) => !d.holiday && !d.attendance.submitted);
  const actions: Action[] = [
    {
      label: "Take attendance",
      hint: pending ? pending.student_group_name : "All registers done",
      icon: ClipboardCheck,
      to: pending ? registerPath(pending.name) : "/classes",
    },
    { label: "My classes", hint: "Registers & students", icon: UsersRound, to: "/classes" },
    { label: "Add homework", hint: "From your CMAP", icon: NotebookPen },
    { label: "Enter marks", hint: "Open exams", icon: PenLine },
  ];
  return (
    <div className="grid grid-cols-2 gap-3">
      {actions.map(({ label, hint, icon: Icon, to }) => {
        const body = (
          <>
            <div className="flex items-start justify-between">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft">
                <Icon className="h-[22px] w-[22px]" />
              </span>
              {!to && <Chip tone="muted">Soon</Chip>}
            </div>
            <div className="min-w-0">
              <p className="text-[15px] font-bold leading-snug">{label}</p>
              <p className="truncate text-xs text-muted">{hint}</p>
            </div>
          </>
        );
        const cls = "flex flex-col gap-3 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60";
        return to ? (
          <Link key={label} to={to} className={clsx(cls, "transition active:scale-[0.98] md:hover:ring-brand/40")}>
            {body}
          </Link>
        ) : (
          <div key={label} className={clsx(cls, "opacity-70")}>
            {body}
          </div>
        );
      })}
    </div>
  );
}

export default function Today() {
  const { data: day, isPending, error, refetch } = useMyDay();
  const dateLabel = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <div>
      <PageTitle title="Today" subtitle={dateLabel} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 lg:items-start">
        <div className="grid min-w-0 grid-cols-1 gap-6 lg:col-span-3">
          <Hero day={day} />
          <section className="grid grid-cols-1 gap-3" aria-labelledby="h-attendance">
            <SectionTitle>
              <span id="h-attendance">Attendance</span>
            </SectionTitle>
            {isPending ? (
              <Skeleton className="h-24" />
            ) : error ? (
              <Card className="text-sm">
                <p className="font-semibold text-bad">{error.message}</p>
                <button type="button" onClick={() => refetch()} className="mt-2 font-semibold text-brand dark:text-brand-soft">
                  Try again
                </button>
              </Card>
            ) : day.divisions.length ? (
              day.divisions.map((d) => <DivisionCard key={d.name} division={d} />)
            ) : (
              <EmptyState icon={<GraduationCap className="h-7 w-7" />} title="No classes assigned yet">
                Ask the school office to add you as an instructor on your division.
              </EmptyState>
            )}
          </section>
        </div>

        <div className="grid min-w-0 grid-cols-1 gap-6 lg:col-span-2">
          <section className="grid grid-cols-1 gap-3" aria-labelledby="h-timetable">
            <SectionTitle>
              <span id="h-timetable">Timetable</span>
            </SectionTitle>
            {isPending ? (
              <Skeleton className="h-48" />
            ) : day?.periods.length ? (
              <Timetable periods={day.periods} />
            ) : (
              <EmptyState icon={<CalendarClock className="h-7 w-7" />} title="No periods today">
                Your divisions have nothing timetabled for {day?.weekday ?? "today"}.
              </EmptyState>
            )}
          </section>
          <section className="grid grid-cols-1 gap-3" aria-labelledby="h-actions">
            <SectionTitle>
              <span id="h-actions">Quick actions</span>
            </SectionTitle>
            <QuickActions day={day} />
          </section>
        </div>
      </div>
    </div>
  );
}
