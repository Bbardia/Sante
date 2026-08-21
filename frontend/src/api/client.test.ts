import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  ApiError,
  tokenStore,
  setUnauthorizedHandler,
  getHealth,
  getMe,
  deleteUser,
  setProductRecipe,
  downloadBackup,
} from "./client";

// Build a minimal Response-like object for the global fetch mock.
function fakeResponse(
  status: number,
  body?: unknown,
  opts: { blob?: boolean } = {}
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: `status ${status}`,
    json: async () => {
      if (body === undefined) throw new Error("no body");
      return body;
    },
    blob: async () => (opts.blob ? new Blob(["data"]) : new Blob()),
  } as unknown as Response;
}

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  localStorage.clear();
  setUnauthorizedHandler(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request()", () => {
  it("attaches a Bearer token when one is stored", async () => {
    tokenStore.set("tok-123");
    fetchMock.mockResolvedValue(fakeResponse(200, { status: "ok" }));

    await getHealth();

    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-123");
  });

  it("omits the Authorization header when no token is stored", async () => {
    fetchMock.mockResolvedValue(fakeResponse(200, { status: "ok" }));

    await getHealth();

    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("returns undefined for a 204 No Content response", async () => {
    fetchMock.mockResolvedValue(fakeResponse(204));
    await expect(deleteUser(5)).resolves.toBeUndefined();
  });

  it("parses a string error detail into the ApiError message", async () => {
    fetchMock.mockResolvedValue(fakeResponse(400, { detail: "Quantity must be greater than 0" }));

    await expect(getHealth()).rejects.toMatchObject({
      status: 400,
      message: "Quantity must be greater than 0",
    });
  });

  it("joins a Pydantic validation-error array into the message", async () => {
    fetchMock.mockResolvedValue(
      fakeResponse(422, {
        detail: [
          { msg: "field required" },
          { msg: "value is not a valid integer" },
        ],
      })
    );

    const err = await getHealth().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("field required; value is not a valid integer");
  });
});

describe("401 handling (auto-logout)", () => {
  it("clears the token and invokes the unauthorized handler on 401", async () => {
    const onUnauth = vi.fn();
    setUnauthorizedHandler(onUnauth);
    tokenStore.set("expired-token");
    fetchMock.mockResolvedValue(fakeResponse(401, { detail: "Not authenticated" }));

    await expect(getMe()).rejects.toBeInstanceOf(ApiError);

    expect(tokenStore.get()).toBeNull();
    expect(onUnauth).toHaveBeenCalledTimes(1);
  });

  it("still clears the token on 401 even with no handler registered", async () => {
    tokenStore.set("expired-token");
    fetchMock.mockResolvedValue(fakeResponse(401, { detail: "Not authenticated" }));

    await expect(getMe()).rejects.toMatchObject({ status: 401 });
    expect(tokenStore.get()).toBeNull();
  });

  it("does NOT clear the token on a 403 (authenticated but forbidden)", async () => {
    const onUnauth = vi.fn();
    setUnauthorizedHandler(onUnauth);
    tokenStore.set("good-token");
    fetchMock.mockResolvedValue(fakeResponse(403, { detail: "Forbidden" }));

    await expect(getMe()).rejects.toMatchObject({ status: 403 });
    expect(tokenStore.get()).toBe("good-token");
    expect(onUnauth).not.toHaveBeenCalled();
  });

  it("logs out on 401 from the binary download helper too", async () => {
    const onUnauth = vi.fn();
    setUnauthorizedHandler(onUnauth);
    tokenStore.set("expired-token");
    fetchMock.mockResolvedValue(fakeResponse(401, { detail: "Not authenticated" }));

    await expect(downloadBackup()).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
    expect(onUnauth).toHaveBeenCalledTimes(1);
  });
});

describe("setProductRecipe contract", () => {
  it("PUTs to /recipes/product/{id} with an { items } body", async () => {
    fetchMock.mockResolvedValue(fakeResponse(200, []));

    await setProductRecipe(7, [
      { ingredient_id: 2, qty: 30 },
      { ingredient_id: 5, qty: 18 },
    ]);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/recipes/product/7");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({
      items: [
        { ingredient_id: 2, qty: 30 },
        { ingredient_id: 5, qty: 18 },
      ],
    });
  });
});
