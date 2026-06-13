import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getTeam } from "@/lib/api";
import { TeamStats } from "@/components/team-stats";

function parseId(raw: string): number | null {
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const numId = parseId(id);
  const data = numId ? await getTeam(numId) : null;
  if (!data) return { title: "Team not found — World Cup 2026" };
  return { title: `${data.team.name} — World Cup 2026` };
}

export default async function TeamPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const numId = parseId(id);
  if (!numId) notFound();

  const data = await getTeam(numId);
  if (!data) notFound();

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/standings"
          className="text-[0.875rem] font-medium text-muted transition-colors hover:text-positive"
        >
          ← Standings
        </Link>
      </div>
      <TeamStats team={data.team} stats={data.stats} form={data.form} />
    </div>
  );
}
