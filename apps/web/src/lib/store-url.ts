import {
  MARKETPLACES,
  SUPPORTED_MARKETPLACES,
  type SupportedMarketplace
} from "@/lib/api/marketplaces";

export type { SupportedMarketplace };

/**
 * Pre-flight check for the add-item form. The API is authoritative — this only
 * spares the user a round trip — so it must not be stricter or looser than
 * `AdapterRegistry.parse` in apps/api/app/providers/adapters.py. Both the host
 * list and the per-marketplace prefixes come from that same source via
 * `pnpm generate:marketplaces`.
 */
export function marketplaceForUrl(value: string): SupportedMarketplace | null {
  // Python removes tab/newline characters anywhere before parsing, while both
  // runtimes trim leading whitespace. Refuse control characters and trailing
  // whitespace so each side evaluates the same submitted URL.
  if (/[\t\r\n]/.test(value) || value !== value.trimEnd()) return null;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  // The API accepts either scheme and canonicalises to https itself.
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  // `_safe_url` rejects any authority carrying credentials or an explicit port.
  // Read that from the raw input rather than url.port, because `new URL()` drops
  // a port equal to the scheme default — so url.port is "" for `:443`, which the
  // adapter still rejects.
  const authority = value.slice(value.indexOf("://") + 3).split(/[/?#]/)[0] ?? "";
  if (authority.includes("@") || /:\d*$/.test(authority)) return null;
  // `\.+$`, not `\.$`: the adapter uses Python's rstrip("."), which removes every
  // trailing root-label dot. Stripping only one would reject a host the API takes.
  const hostname = url.hostname.toLowerCase().replace(/\.+$/, "");
  // WHATWG parsing decodes percent escapes and normalises Unicode dots and
  // backslashes. Python's urlsplit leaves those raw, so accepting a host that
  // changed during parsing would recreate the browser/API drift this check
  // exists to prevent. Preserve only the normalisations both sides share.
  const rawHostname = authority.toLowerCase().replace(/\.+$/, "");
  if (rawHostname !== hostname) return null;

  for (const marketplace of SUPPORTED_MARKETPLACES) {
    const { domains, hostPrefixes } = MARKETPLACES[marketplace];
    // Prefixes are stripped per marketplace, matching each adapter: `smile.` is
    // an Amazon-only host, so smile.ebay.com must not resolve to eBay.
    const prefix = hostPrefixes.find((candidate) => hostname.startsWith(candidate));
    const base = prefix ? hostname.slice(prefix.length) : hostname;
    if (domains.includes(base)) return marketplace;
  }
  return null;
}
