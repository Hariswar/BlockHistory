import Search from "@/components/Search";

export default function Home() {
  return (
    <>
      <section className="hero">
        <h1>What stood on your block?</h1>
        <p>
          Type a street address in Carondelet, St. Louis. BlockHistory looks at the 1938 and 1950
          Sanborn fire insurance maps and lists past uses within 100 meters that sometimes left
          soil or groundwater contamination, like gas stations, garages, dry cleaners and
          foundries.
        </p>
      </section>
      <Search />
    </>
  );
}
