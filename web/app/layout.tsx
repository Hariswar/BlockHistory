import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";
import HeaderNav from "@/components/HeaderNav";
import { yearsText } from "@/lib/site";

// Absolute base for link previews (og:image needs a full URL).
const SITE = process.env.VERCEL_PROJECT_PRODUCTION_URL
  ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
  : "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: "BlockHistory",
  description:
    `See what stood on a St. Louis block in ${yearsText()}, from fire insurance maps, with plain notes on past uses that sometimes left soil contamination.`,
};

const REPORT_URL = "https://github.com/Hariswar/BlockHistory/issues/new";
// Visitor counts (Umami Cloud: no cookies). Off unless the site ID is set. Query strings are
// left out of page views because a search URL holds the address (?q=...).
const UMAMI_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site">
          <div className="wrap">
            <Link href="/" className="brand">
              Block<span>History</span>
            </Link>
            <HeaderNav />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site">
          <div className="wrap">
            <p>
              BlockHistory reads historical maps; it is not an environmental site assessment. A past
              use doesn&apos;t mean the soil is contaminated today, and an empty result doesn&apos;t
              mean it&apos;s clean. For a decision about a property, talk to an environmental
              professional or the Missouri Department of Natural Resources.
            </p>
            <p>
              Maps: Sanborn Map Company, {yearsText()}, from the{" "}
              <a href="https://www.loc.gov/collections/sanborn-maps/">Library of Congress</a>. Base
              map: <a href="https://openfreemap.org">OpenFreeMap</a> ©{" "}
              <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors. A problem
              with the website? <a href={REPORT_URL}>Report it on GitHub</a>, or see its{" "}
              <Link href="/status">status</Link>.
            </p>
          </div>
        </footer>
        {UMAMI_ID && (
          <Script
            src="https://cloud.umami.is/script.js"
            data-website-id={UMAMI_ID}
            data-exclude-search="true"
            strategy="afterInteractive"
          />
        )}
      </body>
    </html>
  );
}
