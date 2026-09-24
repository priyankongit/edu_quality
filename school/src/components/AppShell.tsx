import clsx from "clsx";
import { BookOpenCheck, CircleUserRound, House, UsersRound } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useBrand, useCurrentUser } from "@/lib/queries";
import { Avatar, SchoolLogo } from "./ui";

const TABS = [
  { to: "/", label: "Today", icon: House, end: true },
  { to: "/classes", label: "Classes", icon: UsersRound },
  { to: "/homework", label: "Homework", icon: BookOpenCheck },
  { to: "/me", label: "Me", icon: CircleUserRound },
];

/** Phones get a top bar and bottom tabs; tablets and desktops get a sidebar. */
export default function AppShell() {
  const brand = useBrand();
  const user = useCurrentUser();
  const name = user.instructor?.instructor_name || user.full_name || user.user;

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
          {TABS.map(({ to, label, icon: Icon, end }) => (
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
        <div className="mx-auto grid max-w-xl grid-cols-4 px-2 pt-1.5">
          {TABS.map(({ to, label, icon: Icon, end }) => (
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
                      "grid h-8 w-14 place-items-center rounded-full transition-colors",
                      isActive && "bg-brand-soft dark:bg-brand/25",
                    )}
                  >
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
