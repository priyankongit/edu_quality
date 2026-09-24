import { GraduationCap } from "lucide-react";
import { PageTitle } from "@/components/AppShell";
import DivisionCard from "@/components/DivisionCard";
import { Card, EmptyState, Skeleton } from "@/components/ui";
import { useMyDay } from "@/lib/queries";

export default function Classes() {
  const { data: day, isPending, error, refetch } = useMyDay();
  const total = day?.divisions.reduce((sum, d) => sum + d.attendance.strength, 0) ?? 0;

  return (
    <div>
      <PageTitle
        title="Classes"
        subtitle={day ? `${day.divisions.length} divisions · ${total} students` : "Your divisions and students"}
      />
      {isPending ? (
        <div className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : error ? (
        <Card className="text-sm">
          <p className="font-semibold text-bad">{error.message}</p>
          <button type="button" onClick={() => refetch()} className="mt-2 font-semibold text-brand dark:text-brand-soft">
            Try again
          </button>
        </Card>
      ) : day.divisions.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {day.divisions.map((d) => (
            <DivisionCard key={d.name} division={d} />
          ))}
        </div>
      ) : (
        <EmptyState icon={<GraduationCap className="h-7 w-7" />} title="No classes assigned yet">
          Ask the school office to add you as an instructor on your division.
        </EmptyState>
      )}
    </div>
  );
}
