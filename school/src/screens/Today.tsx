import { CalendarClock, ClipboardCheck, GraduationCap, NotebookPen, PenLine } from "lucide-react";
import type { ComponentType } from "react";
import { PageTitle } from "@/components/AppShell";
import { Card, Chip, EmptyState, SectionTitle } from "@/components/ui";
import { useBrand, useCurrentUser } from "@/lib/queries";

function greeting(date: Date) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

const ACTIONS: { label: string; hint: string; icon: ComponentType<{ className?: string }> }[] = [
  { label: "Take attendance", hint: "Mark your class", icon: ClipboardCheck },
  { label: "Add homework", hint: "From your CMAP", icon: NotebookPen },
  { label: "Enter marks", hint: "Open exams", icon: PenLine },
  { label: "My students", hint: "Profiles & contacts", icon: GraduationCap },
];

export default function Today() {
  const brand = useBrand();
  const user = useCurrentUser();
  const now = new Date();
  const firstName = (user.instructor?.instructor_name || user.full_name || "").split(" ")[0];
  const dateLabel = now.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="grid gap-6">
      <PageTitle title="Today" subtitle={dateLabel} />

      <section className="relative -mt-2 overflow-hidden rounded-4xl bg-brand p-5 text-on-brand shadow-float shadow-brand/30">
        <div aria-hidden className="absolute -right-10 -top-12 h-44 w-44 rounded-full bg-white/10" />
        <div aria-hidden className="absolute -bottom-16 right-10 h-32 w-32 rounded-full bg-white/10" />
        <p className="relative text-sm font-semibold opacity-80">{greeting(now)},</p>
        <p className="relative text-[26px] font-extrabold leading-tight tracking-tight">{firstName || "Teacher"}</p>
        <p className="relative mt-3 max-w-[18rem] text-sm opacity-85">
          {user.instructor?.school || brand.school_name
            ? `Teaching at ${user.instructor?.school || brand.school_name}.`
            : "Welcome to your classroom companion."}
        </p>
      </section>

      <section className="grid gap-3" aria-labelledby="quick-actions">
        <SectionTitle>
          <span id="quick-actions">Quick actions</span>
        </SectionTitle>
        <div className="grid grid-cols-2 gap-3">
          {ACTIONS.map(({ label, hint, icon: Icon }) => (
            <Card key={label} className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft">
                  <Icon className="h-[22px] w-[22px]" />
                </span>
                <Chip tone="muted">Soon</Chip>
              </div>
              <div>
                <p className="text-[15px] font-bold leading-snug">{label}</p>
                <p className="text-xs text-muted">{hint}</p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-3" aria-labelledby="todays-classes">
        <SectionTitle>
          <span id="todays-classes">Your classes today</span>
        </SectionTitle>
        <EmptyState icon={<CalendarClock className="h-7 w-7" />} title="Your timetable lands here next">
          Periods, rooms and attendance status for each class will show up in the next update.
        </EmptyState>
      </section>
    </div>
  );
}
