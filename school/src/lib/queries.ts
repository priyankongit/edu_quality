import { useQuery } from "@tanstack/react-query";
import { boot } from "./boot";
import { call, setCsrfToken } from "./frappe";
import type { Branding, Session } from "./types";

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
