import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { fileUrl } from "@/lib/frappe";
import { useBrand } from "@/lib/queries";

export function SchoolLogo({ size = 40, className }: { size?: number; className?: string }) {
  const brand = useBrand();
  const src = fileUrl(brand.logo || brand.icon);
  const initials = (brand.short_name || brand.app_name).slice(0, 3).toUpperCase();
  return (
    <span
      className={clsx("grid shrink-0 place-items-center overflow-hidden rounded-full bg-white ring-1 ring-black/5", className)}
      style={{ width: size, height: size }}
    >
      {src ? (
        <img src={src} alt={brand.school_name || brand.app_name} className="h-full w-full object-contain" />
      ) : (
        <span className="font-extrabold text-brand" style={{ fontSize: size * 0.32 }}>
          {initials}
        </span>
      )}
    </span>
  );
}

export function Avatar({ name, image, size = 40 }: { name: string; image?: string | null; size?: number }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return (
    <span
      className="grid shrink-0 place-items-center overflow-hidden rounded-full bg-brand-soft font-bold text-brand dark:bg-brand/25 dark:text-brand-soft"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {image ? <img src={fileUrl(image)} alt="" className="h-full w-full object-cover" /> : initials}
    </span>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger";
  loading?: boolean;
};

export function Button({ variant = "primary", loading, className, children, disabled, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl px-5 text-[15px] font-semibold transition active:scale-[0.98] disabled:opacity-60",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand",
        variant === "primary" && "bg-brand text-on-brand shadow-float shadow-brand/30",
        variant === "ghost" && "bg-card text-ink ring-1 ring-line",
        variant === "danger" && "bg-bad/10 text-bad",
        className,
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx("rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60", className)}>{children}</div>;
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between px-1">
      <h2 className="text-[17px] font-bold tracking-tight">{children}</h2>
      {action}
    </div>
  );
}

export function EmptyState({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <Card className="flex flex-col items-center gap-3 px-6 py-10 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft">{icon}</span>
      <h3 className="text-base font-bold">{title}</h3>
      {children && <p className="max-w-xs text-sm text-muted">{children}</p>}
    </Card>
  );
}

export function Chip({ children, tone = "brand" }: { children: ReactNode; tone?: "brand" | "muted" }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide",
        tone === "brand" ? "bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft" : "bg-line/70 text-muted",
      )}
    >
      {children}
    </span>
  );
}
