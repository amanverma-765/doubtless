import { describe, expect, it, vi } from "vitest";
import { ApiError, parseErrorDetail, request } from "@/services/client";

describe("parseErrorDetail", () => {
  it("extracts string detail", () => {
    expect(parseErrorDetail({ detail: "Not found" })).toBe("Not found");
  });

  it("extracts array of validation errors", () => {
    expect(
      parseErrorDetail({ detail: [{ msg: "field required" }, { msg: "invalid" }] })
    ).toBe("field required, invalid");
  });

  it("extracts message fallback", () => {
    expect(parseErrorDetail({ message: "Server error" })).toBe("Server error");
  });

  it("returns undefined for null or non-objects", () => {
    expect(parseErrorDetail(null)).toBeUndefined();
    expect(parseErrorDetail("string")).toBeUndefined();
  });
});

describe("request", () => {
  it("parses JSON response on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ success: true }),
      })
    );

    const data = await request<{ success: boolean }>("/test");
    expect(data).toEqual({ success: true });
  });

  it("throws ApiError on HTTP error status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Video not found" }),
      })
    );

    await expect(request("/missing")).rejects.toThrow(ApiError);
  });
});
