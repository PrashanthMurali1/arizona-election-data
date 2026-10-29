import version from "virtual:election-cache-version";

export function cacheUrl(url: string) {
  const historical = url.match(
    /^\/api\/elections\/az-(\d{4})-(?:us-senate|us-house|governor|attorney-general)(?:$|[-/?])/,
  );
  if (
    !url.startsWith("/api/geography/") &&
    !(historical && Number(historical[1]) <= 2025)
  )
    return url;
  return `${url}${url.includes("?") ? "&" : "?"}ui=${version}`;
}
