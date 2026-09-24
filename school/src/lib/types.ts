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
