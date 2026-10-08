import { ChevronRight, LayoutDashboard, LogOut, Share, SquarePlus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { isStudentView, navItems, PageTitle, phoneTabs } from "@/components/AppShell";
import { Avatar, Button, Card, Chip } from "@/components/ui";
import { logout } from "@/lib/frappe";
import { useBrand, useCurrentUser } from "@/lib/queries";

const PERSONA_LABEL = { teacher: "Teacher", admin: "School admin", guardian: "Parent", student: "Student" } as const;

function isInstalled() {
  const nav = navigator as Navigator & { standalone?: boolean };
  return window.matchMedia("(display-mode: standalone)").matches || nav.standalone === true;
}

export default function Me() {
  const brand = useBrand();
  const user = useCurrentUser();
  const [showInstall, setShowInstall] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const name = user.instructor?.instructor_name || user.student?.student_name || user.full_name || user.user;
  const student = isStudentView(user);
  // Phones only show four tabs; everything else is reached from here.
  const onTabs = phoneTabs(user).map((i) => i.to);
  const more = navItems(user).filter((i) => !onTabs.includes(i.to));

  return (
    <div className="grid grid-cols-1 gap-5">
      <PageTitle title="Me" />

      <nav aria-label="More" className="grid grid-cols-2 gap-3 md:hidden">
        {more.map(({ to, label, hint, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="flex items-center gap-3 rounded-3xl bg-card p-3.5 shadow-card ring-1 ring-line/60 transition active:scale-[0.98]"
          >
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft">
              <Icon className="h-5 w-5" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[15px] font-bold">{label}</span>
              {hint && <span className="block truncate text-xs text-muted">{hint}</span>}
            </span>
          </Link>
        ))}
      </nav>

      <Card className="flex items-center gap-4">
        <Avatar name={name} image={user.user_image} size={64} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-lg font-extrabold tracking-tight">{name}</p>
          <p className="truncate text-sm text-muted">{user.user}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {user.personas.map((p) => (
              <Chip key={p}>{PERSONA_LABEL[p]}</Chip>
            ))}
          </div>
        </div>
      </Card>

      <Card flush className="divide-y divide-line overflow-hidden">
        {user.instructor?.school && (
          <div className="flex items-center justify-between px-4 py-3.5">
            <span className="text-[15px] text-muted">School</span>
            <span className="text-[15px] font-semibold">{user.instructor.school}</span>
          </div>
        )}
        {!isInstalled() && (
          <button
            type="button"
            onClick={() => setShowInstall((v) => !v)}
            aria-expanded={showInstall}
            className="flex w-full items-center gap-3 px-4 py-3.5 text-left"
          >
            <SquarePlus className="h-5 w-5 text-brand dark:text-brand-soft" />
            <span className="flex-1 text-[15px] font-semibold">Add to Home Screen</span>
            <ChevronRight className={`h-5 w-5 text-muted transition-transform ${showInstall ? "rotate-90" : ""}`} />
          </button>
        )}
        {showInstall && (
          <ol className="grid gap-2 bg-brand-soft/40 px-4 py-3.5 text-sm dark:bg-brand/10">
            <li className="flex items-center gap-2">
              <span className="font-bold">1.</span> On iPhone, tap <Share className="inline h-4 w-4" aria-label="Share" /> in Safari.
            </li>
            <li>
              <span className="font-bold">2.</span> Choose <b>Add to Home Screen</b>, then <b>Add</b>.
            </li>
            <li>
              <span className="font-bold">3.</span> Open <b>{brand.short_name}</b> from your home screen, like any other app.
            </li>
          </ol>
        )}
        {!student && (
          <a href="/app" className="flex items-center gap-3 px-4 py-3.5">
            <LayoutDashboard className="h-5 w-5 text-brand dark:text-brand-soft" />
            <span className="flex-1 text-[15px] font-semibold">Open the full ERP</span>
            <ChevronRight className="h-5 w-5 text-muted" />
          </a>
        )}
      </Card>

      <Button
        variant="danger"
        loading={signingOut}
        onClick={() => {
          setSigningOut(true);
          void logout();
        }}
      >
        <LogOut className="h-5 w-5" /> Sign out
      </Button>

      <p className="text-center text-xs text-muted">{brand.app_name}</p>
    </div>
  );
}
