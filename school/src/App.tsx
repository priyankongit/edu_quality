import { useEffect } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import AppShell from "@/components/AppShell";
import { applyBranding } from "@/lib/theme";
import { useBranding, useSession } from "@/lib/queries";
import Login from "@/screens/Login";
import Me from "@/screens/Me";
import Attendance from "@/screens/Attendance";
import Classes from "@/screens/Classes";
import { HomeworkDetail, HomeworkList, NewHomework } from "@/screens/Homework";
import { LoadError, NoAccess, Splash } from "@/screens/Status";
import Today from "@/screens/Today";

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <Today /> },
        { path: "classes", element: <Classes /> },
        { path: "attendance/:division", element: <Attendance /> },
        { path: "homework", element: <HomeworkList /> },
        { path: "homework/new", element: <NewHomework /> },
        { path: "homework/:name", element: <HomeworkDetail /> },
        { path: "me", element: <Me /> },
        { path: "*", element: <Navigate to="/" replace /> },
      ],
    },
  ],
  { basename: "/school" },
);

export default function App() {
  const branding = useBranding();
  const session = useSession();

  useEffect(() => {
    if (branding.data) applyBranding(branding.data);
  }, [branding.data]);

  const failed = branding.error || session.error;
  if (failed) {
    return (
      <LoadError
        message={failed.message}
        onRetry={() => {
          void branding.refetch();
          void session.refetch();
        }}
      />
    );
  }
  if (!branding.data || !session.data) return <Splash />;

  const { personas, user } = session.data;
  if (user === "Guest") return <Login />;
  if (!branding.data.teacher_app_enabled) return <NoAccess reason="disabled" />;
  if (!personas.includes("teacher") && !personas.includes("admin")) return <NoAccess reason="role" />;

  return <RouterProvider router={router} />;
}
