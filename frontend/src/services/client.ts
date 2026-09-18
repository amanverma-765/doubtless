import { API_BASE } from "@/constants/config";

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function parseErrorDetail(errJson: unknown): string | undefined {
  if (!errJson || typeof errJson !== "object") return undefined;
  const obj = errJson as Record<string, unknown>;
  if (Array.isArray(obj.detail)) {
    return obj.detail
      .map((d: { msg?: string } | string) => (typeof d === "string" ? d : d.msg || JSON.stringify(d)))
      .join(", ");
  }
  if (obj.detail && typeof obj.detail === "object") {
    return (obj.detail as { msg?: string }).msg || JSON.stringify(obj.detail);
  }
  if (obj.detail) {
    return String(obj.detail);
  }
  if (obj.message) {
    return String(obj.message);
  }
  return undefined;
}

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errJson = await response.json();
      detail = parseErrorDetail(errJson);
    } catch {
      // Body not JSON
    }

    throw new ApiError(
      detail || `Request failed with status ${response.status}`,
      response.status,
      detail
    );
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
