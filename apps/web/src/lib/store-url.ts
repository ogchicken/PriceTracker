export type SupportedMarketplace = "amazon" | "ebay";

const amazonDomains = new Set([
  "amazon.com",
  "amazon.ca",
  "amazon.com.mx",
  "amazon.com.br",
  "amazon.co.uk",
  "amazon.de",
  "amazon.fr",
  "amazon.it",
  "amazon.es",
  "amazon.nl",
  "amazon.se",
  "amazon.pl",
  "amazon.com.au",
  "amazon.co.jp",
  "amazon.in",
  "amazon.sg",
  "amazon.ae",
  "amazon.sa"
]);

const ebayDomains = new Set([
  "ebay.com",
  "ebay.ca",
  "ebay.co.uk",
  "ebay.de",
  "ebay.fr",
  "ebay.it",
  "ebay.es",
  "ebay.com.au",
  "ebay.at",
  "ebay.be",
  "ebay.ch",
  "ebay.ie",
  "ebay.nl",
  "ebay.pl",
  "ebay.com.sg"
]);

function baseDomain(hostname: string) {
  return hostname.toLowerCase().replace(/^(www|m|smile)\./, "");
}

export function marketplaceForUrl(value: string): SupportedMarketplace | null {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:") return null;
    const hostname = baseDomain(url.hostname);
    if (amazonDomains.has(hostname)) return "amazon";
    if (ebayDomains.has(hostname)) return "ebay";
    return null;
  } catch {
    return null;
  }
}
