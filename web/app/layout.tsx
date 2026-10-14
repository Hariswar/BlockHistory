import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "BlockHistory",
  description:
    "See what stood on a St. Louis block in 1938, from fire insurance maps, with plain notes on past uses that sometimes left soil contamination.",
};

const REPORT_URL = "https://github.com/Hariswar/BlockHistory/issues/new";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site">
          <div className="wrap">
            <Link href="/" className="brand">
              Block<span>History</span>
            </Link>
            <nav>
              <Link href="/">Search</Link>
              <Link href="/about">About &amp; limits</Link>
            </nav>
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
              Maps: Sanborn Map Company, 1938, from the{" "}
              <a href="https://www.loc.gov/collections/sanborn-maps/">Library of Congress</a>. Base
              map: <a href="https://openfreemap.org">OpenFreeMap</a> ©{" "}
              <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors. Found
              a mistake? <a href={REPORT_URL}>Report it</a>.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
