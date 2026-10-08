import clsx from "clsx";
import {
  BookOpenCheck,
  CalendarCheck2,
  CalendarDays,
  House,
  LayoutGrid,
  MessageCircle,
  Newspaper,
  PenLine,
  UsersRound,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useBrand, useCurrentUser, useInbox } from "@/lib/queries";
import type { Session } from "@/lib/types";
import { Avatar, SchoolLogo } from "./ui";

export type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean; hint?: string };

/** A student who isn't also staff gets the student app. */
export function isStudentView(user: Session) {
  return user.personas.includes("student") && !user.personas.includes("teacher") && !user.personas.includes("admin");
}

/** Every screen the user can reach, in sidebar order. Fees and Messages only when they apply. */
export function navItems(user: Session): NavItem[] {
  if (isStudentView(user)) {
    return [
      { to: "/", label: "Today", icon: House, end: true },
      { to: "/homework", label: "Homework", icon: BookOpenCheck, hint: "Set by your teachers" },
      { to: "/attendance", label: "Attendance", icon: CalendarCheck2, hint: "Your days in school" },
      { to: "/fees", label: "Fees", icon: Wallet, hint: "What's paid and due" },
      { to: "/calendar", label: "Calendar", icon: CalendarDays, hint: "Events and holidays" },
      { to: "/newsletters", label: "Newsletters", icon: Newspaper, hint: "News from school" },
    ];
  }
  const f = user.features;
  return [
    { to: "/", label: "Today", icon: House, end: true },
    { to: "/classes", label: "Classes", icon: UsersRound, hint: "Registers & students" },
    { to: "/homework", label: "Homework", icon: BookOpenCheck, hint: "Set and check" },
    { to: "/marks", label: "Marks", icon: PenLine, hint: "Exam marks entry" },
    ...(f?.messages ? [{ to: "/messages", label: "Messages", icon: MessageCircle, hint: "Parents and class channels" }] : []),
    { to: "/calendar", label: "Calendar", icon: CalendarDays, hint: "Events and holidays" },
    ...(f?.fees ? [{ to: "/fees", label: "Fees", icon: Wallet, hint: "Dues in your classes" }] : []),
    { to: "/newsletters", label: "Newsletters", icon: Newspaper, hint: "Sent to families" },
  ];
}

/** Phones have room for five tabs: four screens, then More for the rest. */
export function phoneTabs(user: Session) {
  const wanted = isStudentView(user)
    ? ["/", "/homework", "/attendance", "/fees"]
    : ["/", "/classes", "/homework", "/messages", "/calendar"];
  return navItems(user)
    .filter((i) => wanted.includes(i.to))
    .slice(0, 4);
}

function useUnread(enabled: boolean) {
  const { data } = useInbox(enabled);
  return data?.conversations.reduce((n, c) => n + c.unread, 0) ?? 0;
}

function Badge({ count }: { count: number }) {
  if (!count) return null;
  return (
    <span className="tabular ml-auto grid h-5 min-w-5 place-items-center rounded-full bg-brand px-1.5 text-[11px] font-bold text-on-brand">
      {count > 99 ? "99+" : count}
    </span>
  );
}

/** Phones get a top bar and bottom tabs; tablets and desktops get a sidebar. */
export default function AppShell() {
  const brand = useBrand();
  const user = useCurrentUser();
  const name = user.instructor?.instructor_name || user.student?.student_name || user.full_name || user.user;
  const unread = useUnread(!!user.features?.messages && !isStudentView(user));
  const items = navItems(user);
  const tabs = [...phoneTabs(user), { to: "/me", label: "More", icon: LayoutGrid }];

  return (
    <div className="min-h-[100dvh]">
      {/* Sidebar: tablet and up */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line/80 bg-card md:flex">
        <div className="flex items-center gap-3 px-5 pb-6 pt-7">
          <SchoolLogo size={44} />
          <div className="min-w-0 leading-tight">
            <p className="line-clamp-2 text-[15px] font-extrabold tracking-tight">{brand.school_name || brand.app_name}</p>
            {brand.tagline && <p className="mt-0.5 truncate text-xs text-muted">{brand.tagline}</p>}
          </div>
        </div>
        <nav aria-label="Main" className="grid gap-1 px-3">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[15px] font-semibold transition-colors",
                  isActive
                    ? "bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft"
                    : "text-muted hover:bg-bg hover:text-ink",
                )
              }
            >
              <Icon className="h-5 w-5" aria-hidden />
              {label}
              {to === "/messages" && <Badge count={unread} />}
            </NavLink>
          ))}
        </nav>
        <NavLink to="/me" className="mx-3 mb-5 mt-auto flex items-center gap-3 rounded-2xl p-3 hover:bg-bg">
          <Avatar name={name} image={user.user_image} size={38} />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-bold">{name}</p>
            <p className="truncate text-xs text-muted">{brand.app_name}</p>
          </div>
        </NavLink>
      </aside>

      {/* Top bar: phones */}
      <header className="pt-safe sticky top-0 z-20 bg-bg/85 backdrop-blur-xl backdrop-saturate-150 md:hidden">
        <div className="flex h-14 items-center gap-3 px-4">
          <SchoolLogo size={34} />
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-[15px] font-bold">{brand.school_name || brand.app_name}</p>
            {brand.tagline && <p className="truncate text-xs text-muted">{brand.tagline}</p>}
          </div>
          <NavLink to="/me" aria-label="Your profile">
            <Avatar name={name} image={user.user_image} size={34} />
          </NavLink>
        </div>
      </header>

      <main className="px-4 pb-[calc(96px+env(safe-area-inset-bottom,0px))] pt-2 md:ml-64 md:px-8 md:pb-12 md:pt-8 lg:px-12">
        <div className="mx-auto max-w-xl md:max-w-3xl lg:max-w-5xl">
          <Outlet />
        </div>
      </main>

      {/* Bottom tabs: phones */}
      <nav
        aria-label="Main"
        className="pb-safe fixed inset-x-0 bottom-0 z-20 border-t border-line/80 bg-card/85 backdrop-blur-xl backdrop-saturate-150 md:hidden"
      >
        <div className="mx-auto grid max-w-xl grid-cols-5 px-1 pt-1.5">
          {tabs.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex flex-col items-center gap-1 rounded-2xl py-1.5 text-[11px] font-semibold transition-colors",
                  isActive ? "text-brand dark:text-brand-soft" : "text-muted",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={clsx(
                      "relative grid h-8 w-12 place-items-center rounded-full transition-colors",
                      isActive && "bg-brand-soft dark:bg-brand/25",
                    )}
                  >
                    {to === "/messages" && unread > 0 && (
                      <span className="absolute right-1.5 top-0.5 h-2.5 w-2.5 rounded-full bg-bad ring-2 ring-card" aria-label={`${unread} unread`} />
                    )}
                    <Icon className="h-[22px] w-[22px]" strokeWidth={isActive ? 2.4 : 1.9} aria-hidden />
                  </span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

export function PageTitle({ title, subtitle, back, action }: { title: string; subtitle?: string; back?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-end gap-3 px-1 pb-4 pt-2 md:pb-6 md:pt-0">
      <div className="min-w-0 flex-1">
        {back}
        <h1 className="truncate text-[28px] font-extrabold leading-tight tracking-tight md:text-[32px]">{title}</h1>
        {subtitle && <p className="mt-0.5 text-[15px] text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
