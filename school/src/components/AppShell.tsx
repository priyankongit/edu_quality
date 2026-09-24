import clsx from "clsx";
import { BookOpenCheck, CircleUserRound, House, UsersRound } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useBrand, useCurrentUser } from "@/lib/queries";
import { Avatar, SchoolLogo } from "./ui";

const TABS = [
  { to: "/", label: "Today", icon: House, end: true },
  { to: "/classes", label: "Classes", icon: UsersRound },
  { to: "/homework", label: "Homework", icon: BookOpenCheck },
  { to: "/me", label: "Me", icon: CircleUserRound },
];

export default function AppShell() {
  const brand = useBrand();
  const user = useCurrentUser();
  const { pathname } = useLocation();

  return (
    <div className="mx-auto flex min-h-[100dvh] max-w-xl flex-col">
      <header className="pt-safe sticky top-0 z-20 bg-bg/85 backdrop-blur-xl backdrop-saturate-150">
        <div className="flex h-14 items-center gap-3 px-4">
          <SchoolLogo size={34} />
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-[15px] font-bold">{brand.school_name || brand.app_name}</p>
            {brand.tagline && <p className="truncate text-xs text-muted">{brand.tagline}</p>}
          </div>
          <NavLink to="/me" aria-label="Your profile">
            <Avatar name={user.full_name || user.user} image={user.user_image} size={34} />
          </NavLink>
        </div>
      </header>

      <main key={pathname} className="flex-1 px-4 pb-[calc(96px+env(safe-area-inset-bottom,0px))] pt-2">
        <Outlet />
      </main>

      <nav
        aria-label="Main"
        className="pb-safe fixed inset-x-0 bottom-0 z-20 border-t border-line/80 bg-card/85 backdrop-blur-xl backdrop-saturate-150"
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

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="px-1 pb-4 pt-2">
      <h1 className="text-[28px] font-extrabold leading-tight tracking-tight">{title}</h1>
      {subtitle && <p className="mt-0.5 text-[15px] text-muted">{subtitle}</p>}
    </div>
  );
}
