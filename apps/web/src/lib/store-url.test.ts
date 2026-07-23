import { describe, expect, it } from "vitest";

import { marketplaceForUrl } from "@/lib/store-url";

describe("marketplaceForUrl", () => {
  it("identifies canonical marketplace product URLs", () => {
    expect(marketplaceForUrl("https://www.amazon.com/dp/B08N5WRWNW")).toBe("amazon");
    expect(marketplaceForUrl("https://www.ebay.com/itm/123456789012")).toBe("ebay");
  });

  it("accepts regional domains", () => {
    expect(marketplaceForUrl("https://www.amazon.co.jp/dp/B08N5WRWNW")).toBe("amazon");
    expect(marketplaceForUrl("https://www.ebay.com.sg/itm/123456789012")).toBe("ebay");
  });

  it("accepts the host prefixes each marketplace actually uses", () => {
    expect(marketplaceForUrl("https://m.amazon.de/dp/B08N5WRWNW")).toBe("amazon");
    expect(marketplaceForUrl("https://smile.amazon.com/dp/B08N5WRWNW")).toBe("amazon");
    expect(marketplaceForUrl("https://m.ebay.co.uk/itm/123456789012")).toBe("ebay");
    expect(marketplaceForUrl("https://ebay.com/itm/123456789012")).toBe("ebay");
  });

  it("rejects smile. on eBay, which the API does not recognise", () => {
    // Regression: the browser check used to strip `smile.` from any host, so
    // this URL passed here and then failed with a 422 from the API.
    expect(marketplaceForUrl("https://smile.ebay.com/itm/123456789012")).toBeNull();
  });

  it("accepts http, because the API does and canonicalises it to https", () => {
    expect(marketplaceForUrl("http://www.amazon.com/dp/B08N5WRWNW")).toBe("amazon");
  });

  it("tolerates trailing root-label dots, as the API's rstrip does", () => {
    expect(marketplaceForUrl("https://www.amazon.com./dp/B08N5WRWNW")).toBe("amazon");
  });

  it("rejects credentials and explicit ports, which the API also rejects", () => {
    // Regression: `_safe_url` refuses any authority with userinfo or a port, so
    // accepting these here produced a 422 the user saw as a generic failure.
    expect(marketplaceForUrl("https://user:pass@www.amazon.com/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("https://user@www.amazon.com/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("https://www.amazon.com:8443/dp/B08N5WRWNW")).toBeNull();
    // new URL() drops a port equal to the scheme default, so url.port is "" here
    // and only the raw authority reveals it.
    expect(marketplaceForUrl("https://www.amazon.com:443/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("http://www.amazon.com:80/dp/B08N5WRWNW")).toBeNull();
  });

  it("rejects non-marketplace and malformed URLs", () => {
    expect(marketplaceForUrl("https://example.com/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("https://notamazon.com/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("ftp://www.amazon.com/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("not a url")).toBeNull();
    expect(marketplaceForUrl("")).toBeNull();
  });

  it("rejects lookalike hosts that merely end with a supported domain", () => {
    expect(marketplaceForUrl("https://evil-amazon.com/dp/B08N5WRWNW")).toBeNull();
    expect(marketplaceForUrl("https://amazon.com.evil.test/dp/B08N5WRWNW")).toBeNull();
  });
});
