import { useEffect, useState } from "react";
import { cacheUrl } from "./cacheUrl";
export async function get<T>(
  url: string,
  signal?: AbortSignal,
  cache: RequestCache = "default",
): Promise<T> {
  const response = await fetch(cacheUrl(url), { signal, cache });
  if (!response.ok)
    throw new Error(
      `Unable to load election data (${response.status}). Check that the backend is running and the database has been imported.`,
    );
  return response.json() as Promise<T>;
}
export function useResource<T>(url: string) {
  const [state, setState] = useState<{
    data: T | null;
    error: string | null;
    loading: boolean;
  }>({ data: null, error: null, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, error: null, loading: true });
    get<T>(url, controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name !== "AbortError")
          setState({ data: null, error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [url]);
  return state;
}
