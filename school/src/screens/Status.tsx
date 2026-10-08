import { Loader2, ShieldAlert, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { Button, SchoolLogo } from "@/components/ui";
import { logout } from "@/lib/frappe";

export function Splash() {
  return (
    <div className="grid min-h-[100dvh] place-items-center" aria-busy="true">
      <Loader2 className="h-7 w-7 animate-spin text-brand" aria-label="Loading" />
    </div>
  );
}

function Message({ icon, title, children, action }: { icon: ReactNode; title: string; children: ReactNode; action: ReactNode }) {
  return (
    <div className="pt-safe mx-auto flex min-h-[100dvh] max-w-sm flex-col items-center justify-center gap-4 px-6 text-center">
      {icon}
      <h1 className="text-xl font-extrabold tracking-tight">{title}</h1>
      <p className="text-[15px] text-muted">{children}</p>
      {action}
    </div>
  );
}

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Message
      icon={<WifiOff className="h-10 w-10 text-muted" />}
      title="Couldn't load the app"
      action={<Button onClick={onRetry}>Try again</Button>}
    >
      {message}
    </Message>
  );
}

const NO_ACCESS = {
  disabled: {
    title: "The teacher app is switched off",
    body: "Your school hasn't turned it on yet. An administrator can enable it in School App Settings.",
  },
  "student-disabled": {
    title: "The student app is switched off",
    body: "Your school hasn't turned it on yet. Please check with your class teacher.",
  },
  "not-enrolled": {
    title: "You aren't in a class yet",
    body: "Your account isn't enrolled in a class for this year. Please contact the school office.",
  },
  role: {
    title: "This app is for teachers and students",
    body: "Your account isn't linked to an instructor or a student. Ask the school office to link it.",
  },
};

export function NoAccess({ reason }: { reason: keyof typeof NO_ACCESS }) {
  const { title, body } = NO_ACCESS[reason];
  const staffReason = reason === "disabled" || reason === "role";
  return (
    <Message
      icon={
        <span className="relative">
          <SchoolLogo size={72} />
          <ShieldAlert className="absolute -bottom-1 -right-1 h-7 w-7 rounded-full bg-bg p-0.5 text-bad" />
        </span>
      }
      title={title}
      action={
        <div className="grid w-full gap-2">
          {staffReason && (
            <a href="/app" className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-card font-semibold ring-1 ring-line">
              Open the ERP instead
            </a>
          )}
          <Button variant="danger" onClick={logout}>
            Sign out
          </Button>
        </div>
      }
    >
      {body}
    </Message>
  );
}
