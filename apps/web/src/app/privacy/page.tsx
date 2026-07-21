import { LegalPage } from "@/components/legal-page";

export const metadata = { title: "Privacy" };

const sections = [
  {
    title: "Information the product uses",
    paragraphs: [
      "When connected, PriceTracker uses account identifiers from the authentication provider, product URLs and targets you submit, observed price history, notification preferences, and basic operational logs.",
      "Demo mode uses sample workspace data. Actions in demo mode are simulated and are not stored as a real user watchlist."
    ]
  },
  {
    title: "Why the information is used",
    paragraphs: [
      "The information supports account access, product tracking, price history, target evaluation, notification delivery, abuse prevention, and service reliability.",
      "Server credentials and API tokens stay in the server environment. They are not intentionally included in browser bundles."
    ]
  },
  {
    title: "Service providers",
    paragraphs: [
      "A production deployment may use Clerk for authentication, an email delivery provider, infrastructure hosting, and marketplace data services. The deployment operator should list the providers actually configured and link their privacy terms."
    ]
  },
  {
    title: "Retention and choices",
    paragraphs: [
      "Tracked items and their history should be retained only while needed to provide the workspace or meet legal and security obligations. Users can pause or delete an item and control supported email preferences from the product.",
      "Before launch, the deployment operator should add a verified process for account deletion, data export, privacy requests, retention periods, and jurisdiction-specific rights."
    ]
  },
  {
    title: "Contact",
    paragraphs: [
      "This template is not a substitute for legal advice. Add the production operator’s identity and privacy contact before collecting personal information from real users."
    ]
  }
];

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy"
      summary="A clear overview of the data a connected PriceTracker deployment may process and the controls the product provides."
      sections={sections}
    />
  );
}
