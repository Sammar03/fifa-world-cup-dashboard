import { afterEach, describe, expect, it, vi } from "vitest";

// Verifies the typed client builds the correct backend URL.
describe("api client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("getFixtures calls the backend URL with query params", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ fixtures: [], generated_at: "now" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const api = await import("@/lib/api");
    await api.getFixtures({ status: "live" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    // Reads are cached via Next's Data Cache (ISR) rather than no-store.
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/fixtures?status=live",
      expect.objectContaining({ next: { revalidate: 30 } }),
    );
  });

  it("forces a fresh fetch when revalidate: 0 is passed (live polling)", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ fixtures: [], generated_at: "now" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const api = await import("@/lib/api");
    await api.getFixtures(undefined, { revalidate: 0 });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/fixtures",
      expect.objectContaining({ cache: "no-store" }),
    );
  });
});
