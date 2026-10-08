import { useEffect } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import AppShell from "@/components/AppShell";
import { applyBranding } from "@/lib/theme";
import { useBranding, useSession } from "@/lib/queries";
import Login from "@/screens/Login";
import Me from "@/screens/Me";
import Attendance from "@/screens/Attendance";
import { CalendarScreen, NewEvent } from "@/screens/Calendar";
import { DivisionFeesScreen, FeesOverview } from "@/screens/Fees";
import { MessagesInbox, MessageThread, NewParentMessage } from "@/screens/Messages";
import { NewNewsletter, NewsletterDetail, NewsletterList } from "@/screens/Newsletters";
import Classes from "@/screens/Classes";
import { HomeworkDetail, HomeworkList, NewHomework } from "@/screens/Homework";
import { MarksList, MarksSheet } from "@/screens/Marks";
import { LoadError, NoAccess, Splash } from "@/screens/Status";
import { MyAttendance, MyFeesScreen, MyHomeworkDetail, MyHomeworkList, StudentHome } from "@/screens/Student";
import Today from "@/screens/Today";

const teacherRouter = createBrowserRouter(
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
        { path: "marks", element: <MarksList /> },
        { path: "marks/:plan", element: <MarksSheet /> },
        { path: "messages", element: <MessagesInbox /> },
        { path: "messages/new", element: <NewParentMessage /> },
        { path: "messages/:channel", element: <MessageThread /> },
        { path: "calendar", element: <CalendarScreen /> },
        { path: "calendar/new", element: <NewEvent /> },
        { path: "fees", element: <FeesOverview /> },
        { path: "fees/:division", element: <DivisionFeesScreen /> },
        { path: "newsletters", element: <NewsletterList /> },
        { path: "newsletters/new", element: <NewNewsletter /> },
        { path: "newsletters/:name", element: <NewsletterDetail /> },
        { path: "me", element: <Me /> },
        { path: "*", element: <Navigate to="/" replace /> },
      ],
    },
  ],
  { basename: "/school" },
);

/** Students see their own day, homework, attendance and fees, plus the school calendar and news. */
const studentRouter = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <StudentHome /> },
        { path: "homework", element: <MyHomeworkList /> },
        { path: "homework/:name", element: <MyHomeworkDetail /> },
        { path: "attendance", element: <MyAttendance /> },
        { path: "fees", element: <MyFeesScreen /> },
        { path: "calendar", element: <CalendarScreen /> },
        { path: "newsletters", element: <NewsletterList /> },
        { path: "newsletters/:name", element: <NewsletterDetail /> },
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

  const { personas, user, student } = session.data;
  if (user === "Guest") return <Login />;
  const staff = personas.includes("teacher") || personas.includes("admin");
  if (staff) {
    if (!branding.data.teacher_app_enabled) return <NoAccess reason="disabled" />;
    return <RouterProvider router={teacherRouter} />;
  }
  if (personas.includes("student")) {
    if (branding.data.student_app_enabled === false) return <NoAccess reason="student-disabled" />;
    if (!student?.enrolled) return <NoAccess reason="not-enrolled" />;
    return <RouterProvider router={studentRouter} />;
  }
  return <NoAccess reason="role" />;
}
