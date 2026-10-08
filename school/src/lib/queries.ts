import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { boot } from "./boot";
import { call, setCsrfToken } from "./frappe";
import type {
  AttendanceSummary,
  Branding,
  Calendar,
  DivisionFees,
  EventForm,
  ExamSummary,
  FeeOverview,
  Inbox,
  Message,
  Newsletter,
  NewsletterForm,
  NewsletterSummary,
  ParentContact,
  SchoolEvent,
  StudentAttendance,
  MyFees,
  StudentHome,
  StudentHomework,
  HomeworkDetail,
  HomeworkForm,
  HomeworkStatus,
  HomeworkSummary,
  MarksSheet,
  MyDay,
  Register,
  Session,
} from "./types";

export function useBranding() {
  return useQuery({
    queryKey: ["branding"],
    queryFn: () => call<Branding>("edu_quality.api.school_app.get_branding", undefined, { http: "GET" }),
    initialData: boot.branding,
    staleTime: Infinity,
  });
}

export function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      const session = await call<Session>("edu_quality.api.school_app.get_session", undefined, { http: "GET" });
      setCsrfToken(session.csrf_token);
      return session;
    },
    // A guest page load needs no round trip before showing the sign-in screen.
    initialData: boot.user === "Guest" ? { user: "Guest", personas: [] } : undefined,
    staleTime: 5 * 60 * 1000,
  });
}

/** Branding once the app has loaded it; the shell only renders after that. */
export function useBrand() {
  return useBranding().data as Branding;
}

/** Session for the signed-in user; the shell only renders once signed in. */
export function useCurrentUser() {
  return useSession().data as Session;
}

export function useMyDay() {
  return useQuery({
    queryKey: ["my-day"],
    queryFn: () => call<MyDay>("edu_quality.api.teacher.get_my_day", undefined, { http: "GET" }),
  });
}

export function useRegister(division: string, date: string) {
  return useQuery({
    queryKey: ["register", division, date],
    queryFn: () => call<Register>("edu_quality.api.teacher.get_register", { division, date }, { http: "GET" }),
  });
}

export function useSaveRegister(division: string, date: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ marks, submit }: { marks: Record<string, string>; submit: boolean }) =>
      call<{ attendance: AttendanceSummary; notified: number }>("edu_quality.api.teacher.save_register", {
        division,
        date,
        marks,
        submit: submit ? 1 : 0,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["register", division, date] });
      void client.invalidateQueries({ queryKey: ["my-day"] });
    },
  });
}

export function useHomeworkList() {
  return useQuery({
    queryKey: ["homework"],
    queryFn: () => call<HomeworkSummary[]>("edu_quality.api.teacher.get_homework_list", undefined, { http: "GET" }),
  });
}

export function useHomeworkForm(division: string) {
  return useQuery({
    queryKey: ["homework-form", division],
    queryFn: () => call<HomeworkForm>("edu_quality.api.teacher.get_homework_form", { division }, { http: "GET" }),
    enabled: !!division,
  });
}

export function useHomework(name: string) {
  return useQuery({
    queryKey: ["homework", name],
    queryFn: () => call<HomeworkDetail>("edu_quality.api.teacher.get_homework", { name }, { http: "GET" }),
  });
}

export function useCreateHomework() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: { division: string; title: string; due_date: string; subject?: string; instructions?: string; cmap?: string }) =>
      call<HomeworkSummary>("edu_quality.api.teacher.create_homework", args),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["homework"] }),
  });
}

export function useUpdateHomework(name: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: { updates?: Record<string, { status?: HomeworkStatus; remarks?: string }>; status?: "Open" | "Closed" }) =>
      call<HomeworkSummary>("edu_quality.api.teacher.update_homework", { name, ...args }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["homework"] }),
  });
}

export function useExamList() {
  return useQuery({
    queryKey: ["exams"],
    queryFn: () => call<ExamSummary[]>("edu_quality.api.teacher.get_exam_list", undefined, { http: "GET" }),
  });
}

export function useMarksSheet(plan: string) {
  return useQuery({
    queryKey: ["marks", plan],
    queryFn: () => call<MarksSheet>("edu_quality.api.teacher.get_marks_sheet", { plan }, { http: "GET" }),
  });
}

export function useSaveMarks(plan: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (marks: Record<string, Record<string, string>>) =>
      call<ExamSummary & { saved: number; skipped: number }>("edu_quality.api.teacher.save_marks", { plan, marks }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["marks", plan] });
      void client.invalidateQueries({ queryKey: ["exams"] });
    },
  });
}

// ---------------------------------------------------------------- fees

export function useFeeOverview() {
  return useQuery({
    queryKey: ["fees"],
    queryFn: () => call<FeeOverview>("edu_quality.api.school_fees.get_fee_overview", undefined, { http: "GET" }),
  });
}

export function useDivisionFees(division: string) {
  return useQuery({
    queryKey: ["fees", division],
    queryFn: () => call<DivisionFees>("edu_quality.api.school_fees.get_division_fees", { division }, { http: "GET" }),
  });
}

// ---------------------------------------------------------------- calendar

export function useCalendar(from_date: string, to_date: string) {
  return useQuery({
    queryKey: ["calendar", from_date, to_date],
    queryFn: () => call<Calendar>("edu_quality.api.school_calendar.get_calendar", { from_date, to_date }, { http: "GET" }),
  });
}

export function useEventForm(enabled: boolean) {
  return useQuery({
    queryKey: ["event-form"],
    queryFn: () => call<EventForm>("edu_quality.api.school_calendar.get_event_form", undefined, { http: "GET" }),
    enabled,
    staleTime: 10 * 60 * 1000,
  });
}

export function useCreateEvent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      title: string;
      start: string;
      end: string;
      holiday: boolean;
      description?: string;
      classes: string[];
      school?: string;
    }) =>
      call<SchoolEvent>("edu_quality.api.school_calendar.create_event", { ...args, holiday: args.holiday ? 1 : 0 }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["calendar"] });
      void client.invalidateQueries({ queryKey: ["my-day"] });
    },
  });
}

// ---------------------------------------------------------------- messages

export function useInbox(enabled = true) {
  return useQuery({
    queryKey: ["inbox"],
    queryFn: () => call<Inbox>("edu_quality.api.school_messages.get_conversations", undefined, { http: "GET" }),
    enabled,
    refetchInterval: 30_000,
  });
}

export function useMessages(channel: string) {
  return useQuery({
    queryKey: ["messages", channel],
    queryFn: () =>
      call<{ has_more: boolean; messages: Message[] }>("edu_quality.api.school_messages.get_messages", { channel }, { http: "GET" }),
    // Raven pushes over its own socket; a light poll keeps the thread fresh without wiring that up.
    refetchInterval: 8_000,
  });
}

export function useSendMessage(channel: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => call<{ name: string }>("edu_quality.api.school_messages.send_message", { channel, text }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["messages", channel] });
      void client.invalidateQueries({ queryKey: ["inbox"] });
    },
  });
}

export function useOpenClassChannel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (division: string) =>
      call<{ channel: string; added: number; guardians_on_raven: number; guardians_missing: number }>(
        "edu_quality.api.school_messages.open_class_channel",
        { division },
      ),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["inbox"] }),
  });
}

export function useParentContacts(division: string) {
  return useQuery({
    queryKey: ["parent-contacts", division],
    queryFn: () => call<ParentContact[]>("edu_quality.api.school_messages.get_parent_contacts", { division }, { http: "GET" }),
    enabled: !!division,
  });
}

export function useOpenDirectMessage() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: { guardian: string; division: string }) =>
      call<{ channel: string }>("edu_quality.api.school_messages.open_direct_message", args),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["inbox"] }),
  });
}

// ---------------------------------------------------------------- newsletters

export function useNewsletters() {
  return useQuery({
    queryKey: ["newsletters"],
    queryFn: () =>
      call<{ can_write: boolean; newsletters: NewsletterSummary[] }>("edu_quality.api.school_newsletter.get_newsletters", undefined, {
        http: "GET",
      }),
  });
}

export function useNewsletter(name: string) {
  return useQuery({
    queryKey: ["newsletters", name],
    queryFn: () => call<Newsletter>("edu_quality.api.school_newsletter.get_newsletter", { name }, { http: "GET" }),
  });
}

export function useNewsletterForm() {
  return useQuery({
    queryKey: ["newsletter-form"],
    queryFn: () => call<NewsletterForm>("edu_quality.api.school_newsletter.get_newsletter_form", undefined, { http: "GET" }),
  });
}

export function useSendNewsletter() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: { subject: string; message: string; email_groups: string[]; school?: string }) =>
      call<{ name: string; total_recipients: number }>("edu_quality.api.school_newsletter.send_newsletter", args),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["newsletters"] }),
  });
}

// ---------------------------------------------------------------- student app

export function useStudentHome() {
  return useQuery({
    queryKey: ["student-home"],
    queryFn: () => call<StudentHome>("edu_quality.api.student_app.get_home", undefined, { http: "GET" }),
  });
}

export function useStudentAttendance(month: string) {
  return useQuery({
    queryKey: ["student-attendance", month],
    queryFn: () => call<StudentAttendance>("edu_quality.api.student_app.get_attendance", { month }, { http: "GET" }),
  });
}

export function useStudentHomework() {
  return useQuery({
    queryKey: ["student-homework"],
    queryFn: () => call<StudentHomework[]>("edu_quality.api.student_app.get_homework", undefined, { http: "GET" }),
  });
}

export function useStudentHomeworkDetail(name: string) {
  return useQuery({
    queryKey: ["student-homework", name],
    queryFn: () => call<StudentHomework>("edu_quality.api.student_app.get_homework_detail", { name }, { http: "GET" }),
  });
}

export function useStudentFees() {
  return useQuery({
    queryKey: ["student-fees"],
    queryFn: () => call<MyFees>("edu_quality.api.student_app.get_fees", undefined, { http: "GET" }),
  });
}
