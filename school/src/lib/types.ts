export type Branding = {
  app_name: string;
  short_name: string;
  school_name: string;
  tagline: string;
  logo: string;
  icon: string;
  colors: { primary: string; secondary: string; ink: string };
  teacher_app_enabled: boolean;
};

export type Persona = "teacher" | "admin" | "guardian" | "student";

export type Session = {
  user: string;
  full_name?: string;
  user_image?: string | null;
  personas: Persona[];
  instructor?: {
    name: string;
    instructor_name: string;
    school: string | null;
    image: string | null;
  } | null;
  csrf_token?: string;
};

export type AttendanceSummary = {
  strength: number;
  marked: number;
  present: number;
  absent: number;
  submitted: boolean;
};

export type Division = {
  name: string;
  student_group_name: string;
  program: string;
  school: string | null;
  holiday: boolean;
  attendance: AttendanceSummary;
};

export type Period = {
  name: string;
  division: string;
  division_name: string;
  subject: string;
  subject_name: string | null;
  from_time: string;
  to_time: string;
  type: string | null;
};

export type MyDay = {
  date: string;
  weekday: string;
  divisions: Division[];
  periods: Period[];
};

export type AttendanceStatus = {
  name: string;
  type: "Present" | "Absent" | "Other";
  code: string;
  color: string | null;
};

export type RegisterStudent = {
  student: string;
  student_name: string;
  roll_no: string | null;
  image: string | null;
  status: string | null;
  locked: boolean;
};

export type Register = {
  division: { name: string; student_group_name: string; program: string; school: string | null };
  date: string;
  holiday: boolean;
  statuses: AttendanceStatus[];
  students: RegisterStudent[];
  submitted: boolean;
};

export type HomeworkSummary = {
  name: string;
  title: string;
  division: string;
  division_name: string;
  subject: string | null;
  subject_name: string | null;
  assigned_on: string;
  due_date: string;
  status: "Open" | "Closed";
  total: number;
  submitted: number;
  reviewed: number;
};

export type HomeworkStatus = "Pending" | "Submitted" | "Reviewed";

export type HomeworkDetail = HomeworkSummary & {
  instructions: string | null;
  attachment: string | null;
  submissions: { student: string; student_name: string; roll_no: string | null; status: HomeworkStatus; remarks: string | null }[];
};

export type HomeworkForm = {
  subjects: { name: string; label: string }[];
  suggestions: { cmap: string; subject: string | null; subject_name: string | null; home_work: string }[];
};
