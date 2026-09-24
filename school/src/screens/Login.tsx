import { Eye, EyeOff } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Button, SchoolLogo } from "@/components/ui";
import { login } from "@/lib/frappe";
import { useBrand } from "@/lib/queries";

export default function Login() {
  const brand = useBrand();
  const [usr, setUsr] = useState("");
  const [pwd, setPwd] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!usr.trim() || !pwd) {
      setError("Enter your email and password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await login(usr.trim(), pwd);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[100dvh] flex-col">
      <div className="pt-safe relative overflow-hidden bg-brand-soft dark:bg-brand/25">
        <div aria-hidden className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-brand/10" />
        <div aria-hidden className="absolute -bottom-24 -left-10 h-48 w-48 rounded-full bg-brand/10" />
        <div className="relative mx-auto flex max-w-md flex-col items-center px-6 pb-14 pt-14 text-center">
          <SchoolLogo size={112} className="shadow-float ring-4 ring-white/70" />
          <h1 className="mt-6 text-balance text-[26px] font-extrabold leading-tight tracking-tight">
            {brand.school_name || brand.app_name}
          </h1>
          {brand.tagline && <p className="mt-1.5 text-[15px] font-medium text-muted">{brand.tagline}</p>}
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        noValidate
        className="relative -mt-7 mx-auto flex w-full max-w-md flex-1 flex-col gap-4 rounded-t-4xl bg-bg px-6 pb-[calc(24px+env(safe-area-inset-bottom,0px))] pt-8"
      >
        <div>
          <h2 className="text-xl font-extrabold tracking-tight">Sign in</h2>
          <p className="mt-1 text-sm text-muted">Use the email and password you use for the school ERP.</p>
        </div>

        <label className="grid gap-1.5">
          <span className="text-sm font-semibold">Email or username</span>
          <input
            id="login-usr"
            type="email"
            inputMode="email"
            autoComplete="username"
            autoCapitalize="none"
            value={usr}
            onChange={(e) => setUsr(e.target.value)}
            className="h-12 rounded-2xl bg-card px-4 text-base ring-1 ring-line placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-brand"
            placeholder="name@school.edu"
          />
        </label>

        <label className="grid gap-1.5">
          <span className="text-sm font-semibold">Password</span>
          <span className="relative">
            <input
              id="login-pwd"
              type={showPwd ? "text" : "password"}
              autoComplete="current-password"
              value={pwd}
              onChange={(e) => setPwd(e.target.value)}
              className="h-12 w-full rounded-2xl bg-card pl-4 pr-12 text-base ring-1 ring-line focus:outline-none focus:ring-2 focus:ring-brand"
            />
            <button
              type="button"
              onClick={() => setShowPwd((v) => !v)}
              className="absolute inset-y-0 right-0 grid w-12 place-items-center text-muted"
              aria-label={showPwd ? "Hide password" : "Show password"}
            >
              {showPwd ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </span>
        </label>

        {error && (
          <p role="alert" className="rounded-2xl bg-bad/10 px-4 py-3 text-sm font-medium text-bad">
            {error}
          </p>
        )}

        <Button type="submit" loading={busy} className="mt-1 w-full">
          {busy ? "Signing in…" : "Sign in"}
        </Button>

        <a href="/login#forgot" className="self-center py-2 text-sm font-semibold text-brand dark:text-brand-soft">
          Forgot password?
        </a>

        <p className="mt-auto pt-6 text-center text-xs text-muted">{brand.app_name}</p>
      </form>
    </div>
  );
}
