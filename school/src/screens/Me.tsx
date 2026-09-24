import { ChevronRight, LayoutDashboard, LogOut, Share, SquarePlus } from "lucide-react";
import { useState } from "react";
import { PageTitle } from "@/components/AppShell";
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
  const name = user.instructor?.instructor_name || user.full_name || user.user;

  return (
    <div className="grid grid-cols-1 gap-5">
      <PageTitle title="Me" />

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
        <a href="/app" className="flex items-center gap-3 px-4 py-3.5">
          <LayoutDashboard className="h-5 w-5 text-brand dark:text-brand-soft" />
          <span className="flex-1 text-[15px] font-semibold">Open the full ERP</span>
          <ChevronRight className="h-5 w-5 text-muted" />
        </a>
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
