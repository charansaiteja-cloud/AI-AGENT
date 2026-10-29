import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("api key header", () => {
  it("sends X-API-Key when VITE_API_KEY is configured", async () => {
    vi.stubEnv("VITE_API_KEY", "shared-secret");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("./api");
    await api.health();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["X-API-Key"]).toBe("shared-secret");
  });

  it("does not send an empty X-API-Key", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("./api");
    await api.health();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["X-API-Key"]).toBeUndefined();
  });
});
