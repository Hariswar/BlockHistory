"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Search" },
  { href: "/streets", label: "Streets" },
  { href: "/about", label: "About", also: ["/accuracy"] },
  { href: "/limits", label: "Limits" },
];

// The site's main links, with the current section marked.
export default function HeaderNav() {
  const path = usePathname();
  const current = (l: (typeof LINKS)[number]) =>
    l.href === "/"
      ? path === "/"
      : path.startsWith(l.href) || (l.also ?? []).some((a) => path.startsWith(a));
  return (
    <nav aria-label="Site">
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} aria-current={current(l) ? "page" : undefined}>
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
