import { BookOpenCheck } from "lucide-react";
import { PageTitle } from "@/components/AppShell";
import { EmptyState } from "@/components/ui";

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
