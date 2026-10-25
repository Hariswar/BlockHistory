import Link from "next/link";

// The short info pages, as tabs, so none of them needs a long scroll.
export default function InfoTabs({ active }: { active: "about" | "accuracy" | "limits" }) {
  return (
    <nav className="tabs" aria-label="About BlockHistory">
      <Link href="/about" aria-current={active === "about" ? "page" : undefined}>
        About
      </Link>
      <Link href="/accuracy" aria-current={active === "accuracy" ? "page" : undefined}>
        Accuracy
      </Link>
      <Link href="/limits" aria-current={active === "limits" ? "page" : undefined}>
        Limits &amp; privacy
      </Link>
    </nav>
  );
}
