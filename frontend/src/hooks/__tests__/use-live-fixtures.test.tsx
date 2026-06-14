import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render } from "@testing-library/react";
import type { Fixture } from "@/types";

vi.mock("@/lib/api", () => ({
  getFixtures: vi.fn().mockResolvedValue({ fixtures: [], generated_at: "" }),
}));

import { getFixtures } from "@/lib/api";
import { useLiveFixtures, LIVE_POLL_INTERVAL_MS } from "@/hooks/use-live-fixtures";

function fixture(status: Fixture["status"]): Fixture {
  return {
    id: 1,
    home_team: { id: 1, name: "A", code: "AAA", group_label: "A", flag_url: null },
    away_team: { id: 2, name: "B", code: "BBB", group_label: "A", flag_url: null },
    kickoff_at: "2026-06-12T16:00:00Z",
    venue: null,
    status,
    home_score: null,
    away_score: null,
    group_label: "A",
    round: "Group Stage",
    minute: null,
    verified: false,
  };
}

function Harness({ fixtures }: { fixtures: Fixture[] }) {
  const f = useLiveFixtures(fixtures);
  return <div data-testid="count">{f.length}</div>;
}

describe("useLiveFixtures", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("clears the polling interval on unmount", async () => {
    vi.useFakeTimers();
    const { unmount } = render(<Harness fixtures={[fixture("live")]} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_POLL_INTERVAL_MS);
    });
    expect(getFixtures).toHaveBeenCalledTimes(1);

    unmount();
    vi.mocked(getFixtures).mockClear();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_POLL_INTERVAL_MS * 2);
    });
    expect(getFixtures).not.toHaveBeenCalled();
  });

  it("does not poll when every fixture is finished", async () => {
    vi.useFakeTimers();
    render(<Harness fixtures={[fixture("finished")]} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_POLL_INTERVAL_MS * 2);
    });
    expect(getFixtures).not.toHaveBeenCalled();
  });

  it("polls a scheduled match once its kickoff window is reached", async () => {
    vi.useFakeTimers();
    // Kicked off a minute ago but the page's snapshot still says "scheduled":
    // the hook should poll anyway to catch the live transition.
    const f = fixture("scheduled");
    f.kickoff_at = new Date(Date.now() - 60_000).toISOString();
    render(<Harness fixtures={[f]} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_POLL_INTERVAL_MS);
    });
    expect(getFixtures).toHaveBeenCalled();
  });

  it("does not poll for a scheduled match far from kickoff", async () => {
    vi.useFakeTimers();
    const f = fixture("scheduled");
    f.kickoff_at = new Date(Date.now() + 6 * 60 * 60_000).toISOString(); // 6h away
    render(<Harness fixtures={[f]} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_POLL_INTERVAL_MS * 2);
    });
    expect(getFixtures).not.toHaveBeenCalled();
  });
});
