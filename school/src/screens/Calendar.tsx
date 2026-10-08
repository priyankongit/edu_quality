import clsx from "clsx";
import { CalendarDays, ChevronLeft, ChevronRight, PartyPopper, Plus, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { BackLink, Button, Card, Chip, EmptyState, ErrorCard, inputCls, SectionTitle, Skeleton } from "@/components/ui";
import { formatDay, localISO, parseISO } from "@/lib/dates";
import { useCalendar, useCreateEvent, useCurrentUser, useEventForm } from "@/lib/queries";
import type { SchoolEvent } from "@/lib/types";

function monthBounds(month: string) {
  const [y, m] = month.split("-").map(Number);
  return { from: localISO(new Date(y, m - 1, 1)), to: localISO(new Date(y, m, 0)) };
}

function shiftMonth(month: string, by: number) {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + by, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function daysBetween(a: string, b: string) {
  return Math.round((parseISO(b).getTime() - parseISO(a).getTime()) / 86_400_000);
}

export function whenLabel(e: SchoolEvent) {
  if (e.end !== e.start) {
    const sameMonth = e.start.slice(0, 7) === e.end.slice(0, 7);
    return `${formatDay(e.start, sameMonth ? { day: "numeric" } : { day: "numeric", month: "short" })}–${formatDay(e.end, { day: "numeric", month: "short" })} · ${daysBetween(e.start, e.end) + 1} days`;
  }
  return e.from_time ? `${e.from_time}${e.to_time ? `–${e.to_time}` : ""}` : "All day";
}

function DateBadge({ iso, holiday }: { iso: string; holiday: boolean }) {
  const d = parseISO(iso);
  return (
    <span
      className={clsx(
        "grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-center leading-none",
        holiday ? "bg-warn/15 text-warn" : "bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft",
      )}
    >
      <span>
        <span className="block text-[11px] font-bold uppercase">{d.toLocaleDateString(undefined, { weekday: "short" })}</span>
        <span className="tabular block text-xl font-extrabold">{d.getDate()}</span>
      </span>
    </span>
  );
}

export function EventRow({ event }: { event: SchoolEvent }) {
  const [open, setOpen] = useState(false);
  const past = event.end < localISO();
  return (
    <li className={clsx(past && "opacity-60")}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        disabled={!event.description && event.all_classes}
        className="flex w-full items-center gap-3 p-3 text-left disabled:cursor-default"
      >
        <DateBadge iso={event.start} holiday={event.holiday} />
        <span className="min-w-0 flex-1">
          <span className="mb-1 flex flex-wrap gap-1.5">
            {event.holiday ? <Chip>Holiday</Chip> : event.department && <Chip>{event.department}</Chip>}
            {event.kind && <Chip tone="muted">{event.kind}</Chip>}
          </span>
          <span className="block truncate text-[15px] font-bold">{event.title}</span>
          <span className="block truncate text-sm text-muted">{whenLabel(event)}</span>
        </span>
      </button>
      {open && (
        <div className="grid gap-2 px-4 pb-4 pl-[80px] text-sm">
          {event.description && <p className="whitespace-pre-line">{event.description}</p>}
          {!event.all_classes && event.classes.length > 0 && <p className="text-muted">For {event.classes.join(", ")}</p>}
        </div>
      )}
    </li>
  );
}

type Show = "all" | "holidays" | "events";

export function CalendarScreen() {
  const [params, setParams] = useSearchParams();
  const month = params.get("month") || localISO().slice(0, 7);
  const [show, setShow] = useState<Show>("all");
  const { from, to } = monthBounds(month);
  const { data, isPending, error, refetch } = useCalendar(from, to);

  const events = (data?.events ?? []).filter((e) => show === "all" || (show === "holidays") === e.holiday);
  const title = parseISO(from).toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const holidays = (data?.events ?? []).filter((e) => e.holiday);
  const holidayDays = holidays.reduce((n, e) => n + daysBetween(e.start < from ? from : e.start, e.end > to ? to : e.end) + 1, 0);

  const addButton = data?.can_create && (
    <Link
      to="/calendar/new"
      className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-2xl bg-brand px-4 text-sm font-bold text-on-brand shadow-float shadow-brand/30 active:scale-95"
    >
      <Plus className="h-4 w-4" /> Add
    </Link>
  );

  return (
    <div>
      <PageTitle title="Calendar" subtitle="Events and holidays for your classes" action={addButton} />
      <div className="grid gap-4">
        <Card flush className="flex items-center gap-2 p-2">
          <button
            type="button"
            aria-label="Previous month"
            onClick={() => setParams({ month: shiftMonth(month, -1) })}
            className="grid h-11 w-11 place-items-center rounded-2xl hover:bg-bg"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1 text-center">
            <p className="text-[16px] font-bold">{title}</p>
            {data && (
              <p className="text-xs text-muted">
                {holidayDays ? `${holidayDays} holiday${holidayDays === 1 ? "" : "s"}` : "No holidays"} ·{" "}
                {data.events.length - holidays.length} event{data.events.length - holidays.length === 1 ? "" : "s"}
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Next month"
            onClick={() => setParams({ month: shiftMonth(month, 1) })}
            className="grid h-11 w-11 place-items-center rounded-2xl hover:bg-bg"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </Card>

        <div className="flex gap-2" role="tablist" aria-label="Show">
          {(
            [
              ["all", "Everything"],
              ["holidays", "Holidays"],
              ["events", "Events"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={show === key}
              onClick={() => setShow(key)}
              className={clsx(
                "h-10 rounded-full px-4 text-sm font-bold transition",
                show === key ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {isPending ? (
          <Skeleton className="h-64" />
        ) : error ? (
          <ErrorCard message={error.message} onRetry={() => refetch()} />
        ) : events.length === 0 ? (
          <EmptyState icon={<CalendarDays className="h-7 w-7" />} title={`Nothing in ${title}`}>
            {show === "holidays" ? "No holidays this month." : "No events planned for your classes this month."}
          </EmptyState>
        ) : (
          <Card flush className="overflow-hidden">
            <ul className="divide-y divide-line">
              {events.map((e) => (
                <EventRow key={e.name} event={e} />
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}

/** The next few things on the calendar, for the Today screen. */
export function ComingUp() {
  const today = localISO();
  const inAMonth = new Date();
  inAMonth.setDate(inAMonth.getDate() + 30);
  const { data, isPending } = useCalendar(today, localISO(inAMonth));
  const next = (data?.events ?? []).filter((e) => e.end >= today).slice(0, 3);

  return (
    <section className="grid grid-cols-1 gap-3" aria-labelledby="h-coming-up">
      <SectionTitle
        action={
          <Link to="/calendar" className="text-sm font-semibold text-brand dark:text-brand-soft">
            Calendar
          </Link>
        }
      >
        <span id="h-coming-up">Coming up</span>
      </SectionTitle>
      {isPending ? (
        <Skeleton className="h-24" />
      ) : next.length ? (
        <Card flush className="overflow-hidden">
          <ul className="divide-y divide-line">
            {next.map((e) => (
              <EventRow key={e.name} event={e} />
            ))}
          </ul>
        </Card>
      ) : (
        <Card className="flex items-center gap-3 text-sm text-muted">
          <PartyPopper className="h-5 w-5 shrink-0" /> No holidays or events in the next 30 days.
        </Card>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- new

export function NewEvent() {
  const navigate = useNavigate();
  const user = useCurrentUser();
  const isAdmin = !!user.features?.admin;
  const form = useEventForm(isAdmin);
  const create = useCreateEvent();
  const [title, setTitle] = useState("");
  const [holiday, setHoliday] = useState(false);
  const [start, setStart] = useState(localISO());
  const [end, setEnd] = useState(localISO());
  const [description, setDescription] = useState("");
  const [classes, setClasses] = useState<string[]>([]);
  const [pickedSchool, setPickedSchool] = useState("");
  const schools = form.data?.schools ?? [];
  const school = pickedSchool || schools[0] || "";
  const programs = (form.data?.programs ?? []).filter((p) => !school || p.school === school);

  if (!isAdmin) {
    return (
      <EmptyState icon={<CalendarDays className="h-7 w-7" />} title="Only school admins can add events">
        Ask the school office to put it on the calendar.
      </EmptyState>
    );
  }

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { title, start, end: end < start ? start : end, holiday, description, classes, school: school || undefined },
      { onSuccess: (ev) => navigate(`/calendar?month=${ev.start.slice(0, 7)}`, { replace: true }) },
    );
  };
  const toggle = (program: string) =>
    setClasses((cur) => (cur.includes(program) ? cur.filter((c) => c !== program) : [...cur, program]));

  return (
    <div>
      <PageTitle title={holiday ? "New holiday" : "New event"} back={<BackLink to="/calendar">Calendar</BackLink>} />
      <form onSubmit={submit} className="grid gap-5">
        <div className="grid grid-cols-2 gap-2 rounded-2xl bg-card p-1 ring-1 ring-line" role="radiogroup" aria-label="Kind">
          {[
            { value: false, label: "Event", icon: Sparkles },
            { value: true, label: "Holiday", icon: PartyPopper },
          ].map(({ value, label, icon: Icon }) => (
            <button
              key={label}
              type="button"
              role="radio"
              aria-checked={holiday === value}
              onClick={() => setHoliday(value)}
              className={clsx(
                "inline-flex h-11 items-center justify-center gap-2 rounded-xl text-[15px] font-bold transition",
                holiday === value ? "bg-brand text-on-brand" : "text-muted",
              )}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>

        <label className="grid gap-1.5">
          <span className="px-1 text-sm font-semibold">Name</span>
          <input
            className={clsx(inputCls, "h-12")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={holiday ? "Diwali break" : "Annual sports day"}
            required
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1.5">
            <span className="px-1 text-sm font-semibold">From</span>
            <input
              type="date"
              className={clsx(inputCls, "h-12")}
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                if (end < e.target.value) setEnd(e.target.value);
              }}
              required
            />
          </label>
          <label className="grid gap-1.5">
            <span className="px-1 text-sm font-semibold">To</span>
            <input type="date" className={clsx(inputCls, "h-12")} value={end} min={start} onChange={(e) => setEnd(e.target.value)} required />
          </label>
        </div>

        <label className="grid gap-1.5">
          <span className="px-1 text-sm font-semibold">
            Details <span className="font-normal text-muted">(optional)</span>
          </span>
          <textarea className={clsx(inputCls, "min-h-24 py-3")} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>

        {schools.length > 1 && (
          <label className="grid gap-1.5">
            <span className="px-1 text-sm font-semibold">School</span>
            <select
              className={clsx(inputCls, "h-12")}
              value={school}
              onChange={(e) => {
                setPickedSchool(e.target.value);
                setClasses([]);
              }}
            >
              {schools.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}

        <fieldset className="grid gap-2">
          <legend className="mb-1.5 px-1 text-sm font-semibold">For</legend>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              aria-pressed={classes.length === 0}
              onClick={() => setClasses([])}
              className={clsx(
                "h-10 rounded-full px-4 text-sm font-bold",
                classes.length === 0 ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line",
              )}
            >
              Every class{schools.length > 1 ? ` in ${school}` : ""}
            </button>
            {programs.map((p) => (
              <button
                key={p.name}
                type="button"
                aria-pressed={classes.includes(p.name)}
                onClick={() => toggle(p.name)}
                className={clsx(
                  "h-10 rounded-full px-4 text-sm font-bold",
                  classes.includes(p.name) ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line",
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </fieldset>

        {holiday && (
          <p className="rounded-2xl bg-warn/10 px-4 py-3 text-sm text-warn">
            Attendance can't be taken on these days for the classes you pick.
          </p>
        )}
        {create.error && <p className="px-1 text-sm font-semibold text-bad">{create.error.message}</p>}
        <Button type="submit" loading={create.isPending}>
          Add to calendar
        </Button>
      </form>
    </div>
  );
}
