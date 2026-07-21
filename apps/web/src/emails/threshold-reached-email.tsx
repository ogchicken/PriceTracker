import {
  Body,
  Button,
  Column,
  Container,
  Head,
  Heading,
  Hr,
  Html,
  Preview,
  Row,
  Section,
  Text
} from "react-email";

export interface ThresholdReachedEmailProps {
  itemName: string;
  currentPrice: number;
  previousPrice: number;
  targetPrice: number;
  shippingPrice: number | null;
  currency?: string;
  storeName: string;
  itemUrl: string;
  preferencesUrl: string;
}

const palette = {
  page: "#f2f6f4",
  surface: "#ffffff",
  text: "#18312b",
  muted: "#5e716c",
  border: "#dbe5e1",
  accent: "#167a67",
  accentText: "#ffffff",
  soft: "#e7f3ef"
};

function money(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2
  }).format(value);
}

export function ThresholdReachedEmail({
  itemName,
  currentPrice,
  previousPrice,
  targetPrice,
  shippingPrice,
  currency = "USD",
  storeName,
  itemUrl,
  preferencesUrl
}: ThresholdReachedEmailProps) {
  const total =
    shippingPrice === null ? null : Number((currentPrice + shippingPrice).toFixed(2));

  return (
    <Html lang="en">
      <Head />
      <Preview>
        {itemName} reached your target at {money(currentPrice, currency)}
      </Preview>
      <Body style={styles.body}>
        <Container style={styles.container}>
          <Text style={styles.brand}>PriceTracker</Text>
          <Section style={styles.panel}>
            <Text style={styles.eyebrow}>TARGET REACHED</Text>
            <Heading as="h1" style={styles.heading}>
              The price is now in your range.
            </Heading>
            <Text style={styles.intro}>{itemName}</Text>

            <Section aria-label="Price summary" style={styles.pricePanel}>
              <Row>
                <Column style={styles.priceColumn}>
                  <Text style={styles.label}>Current</Text>
                  <Text style={styles.currentPrice}>{money(currentPrice, currency)}</Text>
                </Column>
                <Column style={styles.priceColumn}>
                  <Text style={styles.label}>Previous</Text>
                  <Text style={styles.price}>{money(previousPrice, currency)}</Text>
                </Column>
                <Column style={styles.priceColumn}>
                  <Text style={styles.label}>Your target</Text>
                  <Text style={styles.price}>{money(targetPrice, currency)}</Text>
                </Column>
              </Row>
            </Section>

            <Section style={styles.details}>
              <Row>
                <Column>
                  <Text style={styles.detailLabel}>Store</Text>
                  <Text style={styles.detailValue}>{storeName}</Text>
                </Column>
                <Column>
                  <Text style={styles.detailLabel}>Shipping</Text>
                  <Text style={styles.detailValue}>
                    {shippingPrice === null
                      ? "Check at store"
                      : shippingPrice === 0
                        ? "Included"
                        : money(shippingPrice, currency)}
                  </Text>
                </Column>
                <Column>
                  <Text style={styles.detailLabel}>Price + shipping</Text>
                  <Text style={styles.detailValue}>
                    {total === null ? "Check at store" : money(total, currency)}
                  </Text>
                </Column>
              </Row>
            </Section>

            <Button
              href={itemUrl}
              aria-label={`View ${itemName} at ${storeName}`}
              style={styles.button}
            >
              View item at {storeName}
            </Button>
            <Text style={styles.disclaimer}>
              Price, shipping, seller, and availability can change. Confirm the final total
              with the store before purchasing.
            </Text>
          </Section>

          <Hr style={styles.rule} />
          <Text style={styles.footer}>
            You received this because this item reached a target in your PriceTracker
            workspace.{" "}
            <a href={preferencesUrl} style={styles.link}>
              Manage notification preferences
            </a>
            .
          </Text>
        </Container>
      </Body>
    </Html>
  );
}

ThresholdReachedEmail.PreviewProps = {
  itemName: "Wireless mechanical keyboard",
  currentPrice: 84.5,
  previousPrice: 99,
  targetPrice: 85,
  shippingPrice: 6.95,
  storeName: "eBay",
  itemUrl: "https://pricetracker.example/items/example",
  preferencesUrl: "https://pricetracker.example/settings"
} satisfies ThresholdReachedEmailProps;

const styles = {
  body: {
    backgroundColor: palette.page,
    color: palette.text,
    fontFamily: "Arial, Helvetica, sans-serif",
    margin: 0,
    padding: "32px 12px"
  },
  container: { margin: "0 auto", maxWidth: "600px" },
  brand: { color: palette.text, fontSize: "18px", fontWeight: "700", margin: "0 0 18px" },
  panel: {
    backgroundColor: palette.surface,
    border: `1px solid ${palette.border}`,
    borderRadius: "14px",
    padding: "32px"
  },
  eyebrow: {
    color: palette.accent,
    fontSize: "12px",
    fontWeight: "700",
    letterSpacing: "1.2px",
    margin: "0 0 10px"
  },
  heading: { color: palette.text, fontSize: "30px", lineHeight: "1.2", margin: "0 0 12px" },
  intro: { color: palette.muted, fontSize: "16px", lineHeight: "1.6", margin: "0 0 24px" },
  pricePanel: {
    backgroundColor: palette.soft,
    borderRadius: "10px",
    margin: "0 0 24px",
    padding: "18px 12px"
  },
  priceColumn: { padding: "0 8px", verticalAlign: "top" as const },
  label: { color: palette.muted, fontSize: "11px", margin: "0 0 6px" },
  currentPrice: { color: palette.accent, fontSize: "22px", fontWeight: "700", margin: 0 },
  price: { color: palette.text, fontSize: "16px", fontWeight: "700", margin: 0 },
  details: { margin: "0 0 24px" },
  detailLabel: { color: palette.muted, fontSize: "11px", margin: "0 0 4px" },
  detailValue: { color: palette.text, fontSize: "13px", fontWeight: "600", margin: 0 },
  button: {
    backgroundColor: palette.accent,
    borderRadius: "8px",
    color: palette.accentText,
    display: "block",
    fontSize: "15px",
    fontWeight: "700",
    padding: "13px 20px",
    textAlign: "center" as const,
    textDecoration: "none"
  },
  disclaimer: { color: palette.muted, fontSize: "12px", lineHeight: "1.6", margin: "18px 0 0" },
  rule: { borderColor: palette.border, margin: "24px 0" },
  footer: { color: palette.muted, fontSize: "12px", lineHeight: "1.6", margin: 0 },
  link: { color: palette.accent, textDecoration: "underline" }
};

export default ThresholdReachedEmail;
