import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { boot } from "./boot";
import { call, setCsrfToken } from "./frappe";
import type { AttendanceSummary, Branding, HomeworkDetail, HomeworkForm, HomeworkStatus, HomeworkSummary, MyDay, Register, Session } from "./types";

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
