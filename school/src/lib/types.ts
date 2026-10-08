export type Branding = {
  app_name: string;
  short_name: string;
  school_name: string;
  tagline: string;
  logo: string;
  icon: string;
  colors: { primary: string; secondary: string; ink: string };
  teacher_app_enabled: boolean;
  student_app_enabled?: boolean;
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
  student?: { name: string; student_name: string; image: string | null; enrolled: boolean } | null;
  features?: { fees: boolean; messages: boolean; admin: boolean };
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

export type ScoringType = "Marks" | "Grades";

export type ExamSummary = {
  name: string;
  assessment_name: string;
  assessment_group: string;
  assessment_group_name: string;
  division: string;
  division_name: string;
  subject: string | null;
  subject_name: string | null;
  schedule_date: string | null;
  maximum_score: number;
  scoring_type: ScoringType;
  exam_type: string | null;
  strength: number;
  entered: number;
  submitted: number;
  mine: boolean;
};

/** A mark ("18"), a grade code ("A+"), "-" for absent, or "" for not entered. */
export type MarkValue = string;

export type MarksSheet = ExamSummary & {
  criteria: { name: string; maximum_score: number }[];
  grades: { code: string; description: string | null }[];
  students: {
    student: string;
    student_name: string;
    roll_no: string | null;
    locked: boolean;
    values: Record<string, string | number>;
  }[];
};

// ---------------------------------------------------------------- fees

export type FeeTotals = {
  billed: number;
  paid: number;
  outstanding: number;
  overdue: number;
  next_due_date: string | null;
};

export type FeeDivision = FeeTotals & {
  name: string;
  student_group_name: string;
  program: string;
  strength: number;
  defaulters: number;
};

export type FeeOverview = { currency: string; divisions: FeeDivision[] };

export type Instalment = { term: string | null; amount: number; due_date: string | null; paid: boolean; overdue: boolean };

export type StudentFees = FeeTotals & {
  student: string;
  student_name: string;
  roll_no: string | null;
  instalments: Instalment[];
};

export type DivisionFees = FeeTotals & {
  division: { name: string; student_group_name: string; program: string };
  academic_year: string | null;
  currency: string;
  students: StudentFees[];
};

// ---------------------------------------------------------------- calendar

export type SchoolEvent = {
  name: string;
  title: string;
  start: string;
  end: string;
  from_time: string | null;
  to_time: string | null;
  holiday: boolean;
  description: string;
  color: string | null;
  all_classes: boolean;
  classes: string[];
  department: string | null;
  kind: string | null;
};

export type EventForm = { schools: string[]; programs: { name: string; label: string; school: string | null }[] };

export type Calendar = { from_date: string; to_date: string; can_create: boolean; events: SchoolEvent[] };

// ---------------------------------------------------------------- messages

export type Conversation = {
  name: string;
  title: string;
  kind: "class" | "direct" | "channel";
  division: string | null;
  image: string | null;
  last_message: string | null;
  last_sender: string | null;
  last_at: string;
  unread: number;
};

export type Inbox = {
  enabled: boolean;
  has_account: boolean;
  conversations: Conversation[];
  divisions: { name: string; student_group_name: string; channel: string | null }[];
};

export type Message = {
  name: string;
  sender: string;
  sender_name: string;
  sender_image: string | null;
  mine: boolean;
  type: string;
  text: string | null;
  file: string | null;
  at: string;
};

export type ParentContact = {
  student: string;
  student_name: string;
  roll_no: string | null;
  guardian: string;
  guardian_name: string;
  on_raven: boolean;
};

// ---------------------------------------------------------------- newsletters

export type NewsletterSummary = {
  name: string;
  subject: string;
  sender_name: string | null;
  sent_at: string | null;
  school: string | null;
  preview: string;
};

export type Newsletter = Omit<NewsletterSummary, "preview"> & {
  recipients: string[];
  total_recipients: number;
  html: string;
  /** The attached PDF, read page by page in the app. */
  pdf: { url: string; pages: { width: number; height: number }[] } | null;
};

export type NewsletterForm = {
  email_groups: { name: string; title: string; total_subscribers: number }[];
  schools: string[];
  sender_name: string | null;
  sender_email: string | null;
};

// ---------------------------------------------------------------- student app

export type AttendanceDay = { date: string; status: string; type: "Present" | "Absent" | "Other"; code: string; color: string | null };

export type AttendanceTotals = { present: number; absent: number; marked: number; percent: number | null };

export type StudentHomework = {
  name: string;
  title: string;
  subject: string | null;
  subject_name: string | null;
  assigned_on: string;
  due_date: string;
  open: boolean;
  status: HomeworkStatus;
  remarks: string | null;
  teacher: string | null;
  instructions: string | null;
  attachment: string | null;
};

export type StudentFeeSummary = { currency: string; outstanding: number; overdue: number; next_due_date: string | null; billed: number };

export type StudentHome = {
  student: {
    name: string;
    student_name: string;
    image: string | null;
    reference_number: string | null;
    roll_no: string | null;
    division: string;
    division_name: string | null;
    school: string | null;
    academic_year: string;
  };
  date: string;
  weekday: string;
  holiday: boolean;
  today: AttendanceDay | null;
  attendance: AttendanceTotals;
  periods: { name: string; subject: string; subject_name: string | null; from_time: string; to_time: string }[];
  homework_due: StudentHomework[];
  fees: StudentFeeSummary;
};

export type StudentAttendance = {
  month: string;
  days: AttendanceDay[];
  holidays: string[];
  statuses: AttendanceStatus[];
  month_totals: AttendanceTotals;
  year_totals: AttendanceTotals;
};

export type MyFees = FeeTotals & { academic_year: string; currency: string; instalments: Instalment[] };
