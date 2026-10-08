import clsx from "clsx";
import { ExternalLink, FileText, Hash, MessageCircle, MessageSquarePlus, SendHorizontal, UserRound, UsersRound } from "lucide-react";
import { Fragment, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { PageTitle } from "@/components/AppShell";
import { Avatar, BackLink, Button, Card, Chip, EmptyState, ErrorCard, inputCls, SectionTitle, Skeleton } from "@/components/ui";
import { fileUrl } from "@/lib/frappe";
import { parseDateTime, shortWhen } from "@/lib/format";
import { useInbox, useMessages, useOpenClassChannel, useOpenDirectMessage, useParentContacts, useSendMessage } from "@/lib/queries";
import type { Conversation, Inbox, Message } from "@/lib/types";

/** Raven keeps messages as editor HTML; show them as plain text so nothing in them can run. */
function messageText(html: string | null) {
  if (!html) return "";
  const withBreaks = html.replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|div|li|h\d)>/gi, "\n");
  return new DOMParser().parseFromString(withBreaks, "text/html").body.textContent?.replace(/\n{3,}/g, "\n\n").trim() ?? "";
}

function threadPath(channel: string) {
  return `/messages/${encodeURIComponent(channel)}`;
}

function Unavailable({ inbox }: { inbox: Inbox }) {
  if (!inbox.enabled)
    return (
      <EmptyState icon={<MessageCircle className="h-7 w-7" />} title="Messaging isn't set up">
        This school hasn't installed Raven yet. Once it has, you can message parents from here.
      </EmptyState>
    );
  return (
    <EmptyState icon={<MessageCircle className="h-7 w-7" />} title="You don't have Raven access yet">
      Ask the school office to give your user the Raven User role, then come back here.
    </EmptyState>
  );
}

function ConversationRow({ c }: { c: Conversation }) {
  const Icon = c.kind === "direct" ? UserRound : c.kind === "class" ? UsersRound : Hash;
  return (
    <li>
      <Link to={threadPath(c.name)} className="flex items-center gap-3 px-4 py-3 transition hover:bg-bg">
        {c.kind === "direct" ? (
          <Avatar name={c.title} image={c.image} size={44} />
        ) : (
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand-soft text-brand dark:bg-brand/25 dark:text-brand-soft">
            <Icon className="h-5 w-5" />
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline gap-2">
            <span className={clsx("min-w-0 flex-1 truncate text-[15px]", c.unread ? "font-extrabold" : "font-bold")}>{c.title}</span>
            <span className="tabular shrink-0 text-xs text-muted">{shortWhen(c.last_at)}</span>
          </span>
          <span className="flex items-center gap-2">
            <span className={clsx("min-w-0 flex-1 truncate text-sm", c.unread ? "font-semibold text-ink" : "text-muted")}>
              {c.last_message ? `${c.kind !== "direct" && c.last_sender ? `${c.last_sender.split(" ")[0]}: ` : ""}${c.last_message}` : "No messages yet"}
            </span>
            {c.unread > 0 && (
              <span className="tabular grid h-5 min-w-5 place-items-center rounded-full bg-brand px-1.5 text-[11px] font-bold text-on-brand">
                {c.unread > 99 ? "99+" : c.unread}
              </span>
            )}
          </span>
        </span>
      </Link>
    </li>
  );
}

function ClassChannels({ inbox }: { inbox: Inbox }) {
  const navigate = useNavigate();
  const open = useOpenClassChannel();
  const missing = inbox.divisions.filter((d) => !d.channel);
  if (!missing.length) return null;
  return (
    <section className="grid gap-3">
      <SectionTitle>Start a class channel</SectionTitle>
      <Card className="grid gap-3">
        <p className="text-sm text-muted">
          One private Raven channel per class, with you, the class's other teachers and every parent on Raven.
        </p>
        <div className="flex flex-wrap gap-2">
          {missing.map((d) => (
            <Button
              key={d.name}
              variant="ghost"
              className="min-h-10 px-4 text-sm"
              loading={open.isPending && open.variables === d.name}
              disabled={open.isPending}
              onClick={() =>
                open.mutate(d.name, {
                  onSuccess: (r) =>
                    navigate(threadPath(r.channel), {
                      state: { joined: r.guardians_on_raven, missing: r.guardians_missing },
                    }),
                })
              }
            >
              <UsersRound className="h-4 w-4" /> {d.student_group_name}
            </Button>
          ))}
        </div>
        {open.error && <p className="text-sm font-semibold text-bad">{open.error.message}</p>}
      </Card>
    </section>
  );
}

export function MessagesInbox() {
  const { data, isPending, error, refetch } = useInbox();
  const ready = data?.enabled && data.has_account;
  const newButton = ready && (
    <Link
      to="/messages/new"
      className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-2xl bg-brand px-4 text-sm font-bold text-on-brand shadow-float shadow-brand/30 active:scale-95"
    >
      <MessageSquarePlus className="h-4 w-4" /> Parent
    </Link>
  );

  return (
    <div>
      <PageTitle title="Messages" subtitle="Classes and parents, through Raven" action={newButton} />
      {isPending ? (
        <Skeleton className="h-64" />
      ) : error ? (
        <ErrorCard message={error.message} onRetry={() => refetch()} />
      ) : !ready ? (
        <Unavailable inbox={data} />
      ) : (
        <div className="grid gap-6">
          {data.conversations.length ? (
            <Card flush className="overflow-hidden">
              <ul className="divide-y divide-line">
                {data.conversations.map((c) => (
                  <ConversationRow key={c.name} c={c} />
                ))}
              </ul>
            </Card>
          ) : (
            <EmptyState icon={<MessageCircle className="h-7 w-7" />} title="No conversations yet">
              Start a channel for one of your classes, or message a parent directly.
            </EmptyState>
          )}
          <ClassChannels inbox={data} />
          <a href="/raven" className="inline-flex items-center gap-1.5 px-1 text-sm font-semibold text-brand dark:text-brand-soft">
            Open Raven for files, threads and reactions <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- new DM

export function NewParentMessage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const inbox = useInbox();
  const division = params.get("division") || inbox.data?.divisions[0]?.name || "";
  const contacts = useParentContacts(division);
  const open = useOpenDirectMessage();
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const shown = (contacts.data ?? []).filter(
    (c) => !q || c.student_name.toLowerCase().includes(q) || c.guardian_name.toLowerCase().includes(q) || c.roll_no === q,
  );

  return (
    <div>
      <PageTitle title="Message a parent" back={<BackLink to="/messages">Messages</BackLink>} />
      <div className="grid gap-4">
        <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Class">
          {(inbox.data?.divisions ?? []).map((d) => (
            <button
              key={d.name}
              type="button"
              role="tab"
              aria-selected={division === d.name}
              onClick={() => setParams({ division: d.name }, { replace: true })}
              className={clsx(
                "h-10 shrink-0 rounded-full px-4 text-sm font-bold",
                division === d.name ? "bg-ink text-bg" : "bg-card text-muted ring-1 ring-line",
              )}
            >
              {d.student_group_name}
            </button>
          ))}
        </div>
        <input
          type="search"
          className={clsx(inputCls, "h-12")}
          placeholder="Search by student or parent"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {open.error && <p className="px-1 text-sm font-semibold text-bad">{open.error.message}</p>}
        {contacts.isPending ? (
          <Skeleton className="h-64" />
        ) : contacts.error ? (
          <ErrorCard message={contacts.error.message} onRetry={() => contacts.refetch()} />
        ) : shown.length === 0 ? (
          <p className="px-1 text-sm text-muted">{q ? "No one matches that." : "No parents are linked to students in this class."}</p>
        ) : (
          <Card flush className="overflow-hidden">
            <ul className="divide-y divide-line">
              {shown.map((c) => (
                <li key={`${c.student}-${c.guardian}`}>
                  <button
                    type="button"
                    disabled={!c.on_raven || open.isPending}
                    onClick={() =>
                      open.mutate({ guardian: c.guardian, division }, { onSuccess: (r) => navigate(threadPath(r.channel), { replace: true }) })
                    }
                    className="flex w-full items-center gap-3 px-4 py-3 text-left transition enabled:hover:bg-bg disabled:opacity-60"
                  >
                    <span className="tabular w-8 shrink-0 text-sm font-semibold text-muted">{c.roll_no || "–"}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[15px] font-bold">{c.guardian_name}</span>
                      <span className="block truncate text-sm text-muted">Parent of {c.student_name}</span>
                    </span>
                    {!c.on_raven && <Chip tone="muted">Not on Raven</Chip>}
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- thread

function Bubble({ m, showName }: { m: Message; showName: boolean }) {
  const time = parseDateTime(m.at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return (
    <li className={clsx("flex items-end gap-2", m.mine && "flex-row-reverse")}>
      {!m.mine && (showName ? <Avatar name={m.sender_name} image={m.sender_image} size={28} /> : <span className="w-7 shrink-0" />)}
      <div
        className={clsx(
          "max-w-[80%] rounded-3xl px-4 py-2.5 md:max-w-[65%]",
          m.mine ? "rounded-br-lg bg-brand text-on-brand" : "rounded-bl-lg bg-card ring-1 ring-line/60",
        )}
      >
        {showName && !m.mine && <p className="mb-0.5 text-xs font-bold text-brand dark:text-brand-soft">{m.sender_name}</p>}
        {m.type === "Image" && m.file ? (
          <a href={fileUrl(m.file)} target="_blank" rel="noreferrer">
            <img src={fileUrl(m.file)} alt="" className="max-h-64 rounded-2xl" loading="lazy" />
          </a>
        ) : m.type === "File" && m.file ? (
          <a href={fileUrl(m.file)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 font-semibold underline">
            <FileText className="h-4 w-4" /> {decodeURIComponent(m.file.split("/").pop() || "File")}
          </a>
        ) : m.type === "Text" ? (
          <p className="whitespace-pre-wrap break-words text-[15px]">{messageText(m.text)}</p>
        ) : (
          <p className="text-sm italic opacity-80">{m.type} — open Raven to see it</p>
        )}
        <p className={clsx("tabular mt-0.5 text-right text-[11px]", m.mine ? "opacity-75" : "text-muted")}>{time}</p>
      </div>
    </li>
  );
}

function dayLabel(at: string) {
  const d = parseDateTime(at);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
}

export function MessageThread() {
  const { channel = "" } = useParams();
  const location = useLocation();
  const [joined, setJoined] = useState(location.state as { joined: number; missing: number } | null);
  const resync = useOpenClassChannel();
  const inbox = useInbox();
  const { data, isPending, error, refetch } = useMessages(channel);
  const send = useSendMessage(channel);
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const conversation = inbox.data?.conversations.find((c) => c.name === channel);
  const lastId = data?.messages[data.messages.length - 1]?.name;

  useLayoutEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [lastId]);
  // Opening a thread marks it read on the server; refresh the unread badges.
  useEffect(() => {
    if (data) void inbox.refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [!!data]);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const body = text.trim();
    if (!body || send.isPending) return;
    send.mutate(body, { onSuccess: () => setText("") });
  };
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends on a keyboard; phones keep Enter for new lines.
    if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(pointer: fine)").matches) {
      e.preventDefault();
      submit();
    }
  };

  const messages = data?.messages ?? [];
  return (
    <div className="flex min-h-[calc(100dvh-180px)] flex-col md:min-h-[calc(100dvh-80px)]">
      <PageTitle
        title={conversation?.title ?? "Conversation"}
        subtitle={conversation?.kind === "class" ? "Class channel · parents and teachers" : conversation?.kind === "direct" ? "Direct message" : undefined}
        back={<BackLink to="/messages">Messages</BackLink>}
        action={
          conversation?.kind === "class" &&
          conversation.division && (
            <Button
              variant="ghost"
              className="min-h-10 shrink-0 px-3 text-sm"
              loading={resync.isPending}
              onClick={() =>
                resync.mutate(conversation.division!, {
                  onSuccess: (r) => setJoined({ joined: r.guardians_on_raven, missing: r.guardians_missing }),
                })
              }
            >
              <UsersRound className="h-4 w-4" /> Add parents
            </Button>
          )
        }
      />
      {resync.error && <p className="mb-3 text-sm font-semibold text-bad">{resync.error.message}</p>}
      {joined && (
        <p className="mb-3 rounded-2xl bg-brand-soft px-4 py-3 text-sm text-brand dark:bg-brand/20 dark:text-brand-soft">
          {joined.joined} parent{joined.joined === 1 ? " is" : "s are"} in this channel.
          {joined.missing > 0 && ` ${joined.missing} aren't on Raven yet; the school office can give them access, then tap Add parents.`}
        </p>
      )}
      <div className="flex-1">
        {isPending ? (
          <Skeleton className="h-64" />
        ) : error ? (
          <ErrorCard message={error.message} onRetry={() => refetch()} />
        ) : messages.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted">No messages yet. Say hello.</p>
        ) : (
          <ol className="grid gap-1.5 pb-4">
            {data.has_more && (
              <li className="pb-2 text-center text-xs text-muted">
                Showing the latest {messages.length}.{" "}
                <a href="/raven" className="font-semibold text-brand dark:text-brand-soft">
                  Older ones are in Raven
                </a>
              </li>
            )}
            {messages.map((m, i) => {
              const prev = messages[i - 1];
              const newDay = !prev || parseDateTime(prev.at).toDateString() !== parseDateTime(m.at).toDateString();
              return (
                <Fragment key={m.name}>
                  {newDay && (
                    <li className="py-2 text-center text-xs font-semibold text-muted" role="separator">
                      {dayLabel(m.at)}
                    </li>
                  )}
                  <Bubble m={m} showName={newDay || prev.sender !== m.sender} />
                </Fragment>
              );
            })}
          </ol>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={submit}
        className="sticky bottom-[calc(80px+env(safe-area-inset-bottom,0px))] z-10 -mx-4 mt-2 flex items-end gap-2 bg-bg/90 px-4 py-2 backdrop-blur-xl md:bottom-0 md:mx-0 md:px-0"
      >
        <label className="sr-only" htmlFor="composer">
          Message
        </label>
        <textarea
          id="composer"
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Write a message"
          maxLength={4000}
          className={clsx(inputCls, "max-h-40 min-h-12 resize-none py-3")}
        />
        <button
          type="submit"
          aria-label="Send"
          disabled={!text.trim() || send.isPending}
          className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-brand text-on-brand shadow-float shadow-brand/30 transition active:scale-95 disabled:opacity-50"
        >
          <SendHorizontal className="h-5 w-5" />
        </button>
      </form>
      {send.error && <p className="pt-1 text-sm font-semibold text-bad">{send.error.message}</p>}
    </div>
  );
}
