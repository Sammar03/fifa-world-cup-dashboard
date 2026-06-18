import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getFixture } from "@/lib/api";
import { MatchView } from "@/components/match/match-view";

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
  const data = numId ? await getFixture(numId) : null;
  if (!data) return { title: "Match not found — World Cup 2026" };
  const { home_team, away_team } = data.fixture;
  return {
    title: `${home_team.name} vs ${away_team.name} — World Cup 2026`,
  };
}

export default async function MatchPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const numId = parseId(id);
  if (!numId) notFound();

  const data = await getFixture(numId);
  if (!data) notFound();

  return <MatchView initial={data} />;
}
