import { getFixtures } from "@/lib/api";
import { FixturesBoard } from "@/components/fixtures-board";
import { NLQueryBox } from "@/components/nl-query-box";

// Home: live + upcoming fixtures grouped by day. Server Component — data is
// fetched server-side from the dashboard's own API (CLAUDE.md §7.2).
export default async function HomePage() {
  const { fixtures } = await getFixtures();

  return (
    <div className="space-y-8">
      <header className="rise-in py-2">
        <h1 className="display text-[3rem] md:text-[4rem]">Fixtures</h1>
        <span className="title-accent" aria-hidden />
      </header>

      <FixturesBoard initialFixtures={fixtures} />

      <NLQueryBox />
    </div>
  );
}
