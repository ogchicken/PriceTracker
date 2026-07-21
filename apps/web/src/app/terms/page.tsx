import { LegalPage } from "@/components/legal-page";

export const metadata = { title: "Terms" };

const sections = [
  {
    title: "Using PriceTracker",
    paragraphs: [
      "PriceTracker helps you organize product links, observed prices, targets, and notifications. You are responsible for the links and target values you add and for complying with marketplace terms when using those marketplaces.",
      "You may not use the service to interfere with the product, access another person’s workspace, or submit unlawful or harmful material."
    ]
  },
  {
    title: "Price and availability information",
    paragraphs: [
      "Prices, shipping, seller details, and availability can change at any time. Information shown in PriceTracker may be delayed, incomplete, or different from the final marketplace checkout price.",
      "An alert is informational, not a guarantee that an item remains available or can be purchased at the observed price. Verify all details with the marketplace before purchasing."
    ]
  },
  {
    title: "Accounts and notifications",
    paragraphs: [
      "When account features are enabled, keep your access credentials secure. Notification delivery can be delayed or blocked by email providers and should not be treated as time-critical communication."
    ]
  },
  {
    title: "Service changes",
    paragraphs: [
      "Supported stores, checks, and features may change as the product evolves."
    ]
  },
  {
    title: "Contact",
    paragraphs: [
      "A production deployment should replace this section with the operator’s legal name, support address, governing law, and any jurisdiction-specific consumer terms before accepting users."
    ]
  }
];

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of use"
      summary="These product-shaped terms explain the expected use of PriceTracker. Deployment owners should obtain legal review and add their operator details before launch."
      sections={sections}
    />
  );
}
