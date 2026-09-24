import { BookOpenCheck, UsersRound } from "lucide-react";
import { PageTitle } from "@/components/AppShell";
import { EmptyState } from "@/components/ui";

export function Classes() {
  return (
    <div>
      <PageTitle title="Classes" subtitle="Your divisions and students" />
      <EmptyState icon={<UsersRound className="h-7 w-7" />} title="Your classes are on the way">
        Class lists, attendance and student profiles arrive in the next update.
      </EmptyState>
    </div>
  );
}

export function Homework() {
  return (
    <div>
      <PageTitle title="Homework" subtitle="Assign, collect and review" />
      <EmptyState icon={<BookOpenCheck className="h-7 w-7" />} title="Homework is coming soon">
        You'll be able to set homework from your CMAP and review what students hand in.
      </EmptyState>
    </div>
  );
}
