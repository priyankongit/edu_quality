import clsx from "clsx";
import { ChevronRight, Download, Mail, Newspaper, PenSquare, Send } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { BackLink, Button, Card, Chip, EmptyState, ErrorCard, inputCls, Skeleton } from "@/components/ui";
import { parseDateTime } from "@/lib/format";
import { fileUrl } from "@/lib/frappe";
import { useNewsletter, useNewsletterForm, useNewsletters, useSendNewsletter } from "@/lib/queries";
import type { Newsletter } from "@/lib/types";

function sentLabel(at: string | null) {
  if (!at) return "";
  return parseDateTime(at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
}

export function NewsletterList() {
  const { data, isPending, error, refetch } = useNewsletters();
  const writeButton = data?.can_write && (
    <Link
      to="/newsletters/new"
      className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-2xl bg-brand px-4 text-sm font-bold text-on-brand shadow-float shadow-brand/30 active:scale-95"
    >
      <PenSquare className="h-4 w-4" /> Write
    </Link>
  );

  return (
    <div>
      <PageTitle title="Newsletters" subtitle="What the school has sent to families" action={writeButton} />
      {isPending ? (
        <div className="grid gap-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : data.newsletters.length === 0 ? (
        <EmptyState icon={<Newspaper className="h-7 w-7" />} title="No newsletters yet">
          Newsletters the school emails to parents will show here once they go out.
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {data.newsletters.map((n) => (
            <Link
              key={n.name}
              to={`/newsletters/${encodeURIComponent(n.name)}`}
              className="group grid gap-2 rounded-3xl bg-card p-4 shadow-card ring-1 ring-line/60 transition active:scale-[0.99] md:hover:ring-brand/40"
            >
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-muted">
                    {sentLabel(n.sent_at)}
                    {n.sender_name && ` · ${n.sender_name}`}
                  </p>
                  <p className="line-clamp-2 text-[16px] font-bold leading-snug">{n.subject}</p>
                </div>
                <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted transition group-hover:translate-x-0.5" />
              </div>
              {n.preview && <p className="line-clamp-2 text-sm text-muted">{n.preview}</p>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/** Newsletter bodies are email HTML; render them in a sandbox that can't run scripts or reach the app. */
function NewsletterBody({ html }: { html: string }) {
  const [height, setHeight] = useState(400);
  const doc = `<!doctype html><html><head><meta charset="utf-8"><base target="_blank">
<style>body{margin:0;padding:20px;font:16px/1.6 system-ui,-apple-system,sans-serif;color:#1f2328;background:#fff;word-wrap:break-word}
img{max-width:100%;height:auto}table{max-width:100%}a{color:#3346d3}</style></head><body>${html}</body></html>`;
  return (
    <iframe
      title="Newsletter"
      srcDoc={doc}
      sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
      className="w-full rounded-3xl bg-white ring-1 ring-line/60"
      style={{ height }}
      onLoad={(e) => {
        const body = e.currentTarget.contentDocument?.body;
        if (body) setHeight(body.scrollHeight + 8);
      }}
    />
  );
}

function pageUrl(name: string, page: number) {
  return `/api/method/edu_quality.api.school_newsletter.get_newsletter_page?name=${encodeURIComponent(name)}&page=${page}`;
}

/** The newsletter's PDF as a column of page images; pinch to zoom like any web page. */
function PdfPages({ newsletter }: { newsletter: Newsletter }) {
  const pdf = newsletter.pdf!;
  return (
    <ol className="-mx-4 grid gap-3 md:mx-0">
      {pdf.pages.map((p, i) => (
        <li key={i} className="grid gap-1">
          <img
            src={pageUrl(newsletter.name, i + 1)}
            alt={`${newsletter.subject}, page ${i + 1}`}
            loading={i < 2 ? "eager" : "lazy"}
            decoding="async"
            width={p.width}
            height={p.height}
            className="h-auto w-full bg-white shadow-card md:rounded-2xl md:ring-1 md:ring-line/60"
            style={{ aspectRatio: `${p.width} / ${p.height}` }}
          />
          <span className="tabular px-4 text-center text-xs text-muted md:px-0">
            Page {i + 1} of {pdf.pages.length}
          </span>
        </li>
      ))}
    </ol>
  );
}

export function NewsletterDetail() {
  const { name = "" } = useParams();
  const { data, isPending, error, refetch } = useNewsletter(name);
  const [tab, setTab] = useState<"read" | "summary">("read");
  const showPages = !!data?.pdf && tab === "read";

  return (
    <div>
      <PageTitle
        title={data?.subject ?? "Newsletter"}
        subtitle={data ? [sentLabel(data.sent_at), data.sender_name].filter(Boolean).join(" · ") : undefined}
        back={<BackLink to="/newsletters">Newsletters</BackLink>}
      />
      {isPending ? (
        <Skeleton className="h-96" />
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : (
        <div className="grid gap-3">
          {data.pdf && (
            <div className="flex items-center gap-2">
              <div className="flex gap-2" role="tablist" aria-label="View">
                {(
                  [
                    ["read", `Read · ${data.pdf.pages.length} pages`],
                    ["summary", "In this issue"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={tab === key}
                    onClick={() => setTab(key)}
                    className={clsx("h-10 rounded-full px-4 text-sm font-bold", tab === key ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line")}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <a
                href={fileUrl(data.pdf.url)}
                download
                aria-label="Download PDF"
                className="ml-auto grid h-10 w-10 shrink-0 place-items-center rounded-full bg-card text-brand ring-1 ring-line dark:text-brand-soft"
              >
                <Download className="h-5 w-5" />
              </a>
            </div>
          )}
          {showPages ? (
            <PdfPages newsletter={data} />
          ) : (
            <>
              {data.recipients.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 px-1">
                  {data.recipients.map((r) => (
                    <Chip key={r} tone="muted">
                      {r}
                    </Chip>
                  ))}
                  {data.total_recipients > 0 && <span className="text-xs text-muted">{data.total_recipients} recipients</span>}
                </div>
              )}
              <NewsletterBody html={data.html} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function NewNewsletter() {
  const navigate = useNavigate();
  const form = useNewsletterForm();
  const send = useSendNewsletter();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [groups, setGroups] = useState<string[]>([]);
  const [school, setSchool] = useState("");
  const [confirming, setConfirming] = useState(false);

  const recipients = (form.data?.email_groups ?? [])
    .filter((g) => groups.includes(g.name))
    .reduce((n, g) => n + (g.total_subscribers || 0), 0);
  const schools = form.data?.schools ?? [];

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!confirming) {
      setConfirming(true);
      return;
    }
    send.mutate(
      { subject, message, email_groups: groups, school: school || undefined },
      { onSuccess: (r) => navigate(`/newsletters/${encodeURIComponent(r.name)}`, { replace: true }) },
    );
  };

  if (form.error) {
    return (
      <div>
        <PageTitle title="New newsletter" back={<BackLink to="/newsletters">Newsletters</BackLink>} />
        <ErrorCard message={form.error.message} onRetry={() => form.refetch()} />
      </div>
    );
  }

  return (
    <div>
      <PageTitle title="New newsletter" back={<BackLink to="/newsletters">Newsletters</BackLink>} />
      {form.data && !form.data.sender_email && (
        <Card className="mb-5 flex items-start gap-3 bg-warn/10 ring-warn/30">
          <Mail className="mt-0.5 h-5 w-5 shrink-0 text-warn" />
          <p className="text-sm">The site has no outgoing email account yet, so newsletters can't be sent. Ask whoever runs the ERP to set one up.</p>
        </Card>
      )}
      <form onSubmit={submit} className="grid gap-5" onChange={() => setConfirming(false)}>
        <label className="grid gap-1.5">
          <span className="px-1 text-sm font-semibold">Subject</span>
          <input className={clsx(inputCls, "h-12")} value={subject} onChange={(e) => setSubject(e.target.value)} required />
        </label>
        <label className="grid gap-1.5">
          <span className="px-1 text-sm font-semibold">Message</span>
          <textarea
            className={clsx(inputCls, "min-h-64 py-3")}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Leave a blank line between paragraphs."
            required
          />
        </label>

        <fieldset className="grid gap-2">
          <legend className="mb-1.5 px-1 text-sm font-semibold">Send to</legend>
          {form.isPending ? (
            <Skeleton className="h-12" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {form.data.email_groups.map((g) => {
                const on = groups.includes(g.name);
                return (
                  <button
                    key={g.name}
                    type="button"
                    aria-pressed={on}
                    onClick={() => {
                      setConfirming(false);
                      setGroups((cur) => (on ? cur.filter((x) => x !== g.name) : [...cur, g.name]));
                    }}
                    className={clsx("h-10 rounded-full px-4 text-sm font-bold", on ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line")}
                  >
                    {g.title || g.name} <span className="tabular opacity-70">{g.total_subscribers}</span>
                  </button>
                );
              })}
            </div>
          )}
        </fieldset>

        {schools.length > 1 && (
          <label className="grid gap-1.5">
            <span className="px-1 text-sm font-semibold">
              Show in the app for <span className="font-normal text-muted">(optional)</span>
            </span>
            <select className={clsx(inputCls, "h-12")} value={school} onChange={(e) => setSchool(e.target.value)}>
              <option value="">Every school</option>
              {schools.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}

        {confirming && (
          <Card className="flex items-start gap-3 bg-warn/10 ring-warn/30">
            <Mail className="mt-0.5 h-5 w-5 shrink-0 text-warn" />
            <p className="text-sm">
              This emails <b>{recipients}</b> {recipients === 1 ? "person" : "people"} straight away and can't be recalled. Tap Send
              now to go ahead.
            </p>
          </Card>
        )}
        {send.error && <p className="px-1 text-sm font-semibold text-bad">{send.error.message}</p>}
        <Button type="submit" loading={send.isPending} disabled={!groups.length || (!!form.data && !form.data.sender_email)}>
          <Send className="h-4 w-4" /> {confirming ? "Send now" : "Review and send"}
        </Button>
      </form>
    </div>
  );
}
