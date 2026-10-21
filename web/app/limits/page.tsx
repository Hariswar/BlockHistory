import InfoTabs from "@/components/InfoTabs";

export const metadata = { title: "Limits & privacy · BlockHistory" };

export default function Limits() {
  return (
    <article className="prose">
      <InfoTabs active="limits" />
      <h1>What BlockHistory can&apos;t tell you</h1>
      <ul>
        <li>
          <strong>This is not an environmental site assessment.</strong> A past use doesn&apos;t
          mean the soil is contaminated today, and no listing doesn&apos;t mean it&apos;s clean.
        </li>
        <li>
          Two years only: businesses that opened and closed between 1938 and 1950, or after 1950,
          don&apos;t show. &ldquo;Not on the 1950 map&rdquo; can also mean the reader missed it.
        </li>
        <li>
          Addresses are placed with the City of St. Louis address service, usually on the
          property&apos;s parcel (within about 15–40 m); otherwise along the street or by the US
          Census, which can be 30–80 m off. Each search says which.
        </li>
        <li>
          State records are shown as the Missouri Department of Natural Resources words them, from
          its public E-START data. Tanks only had to be registered from 1986, so older tanks often
          have no record; a record at the same spot as an old listing may be a later business.
        </li>
        <li>
          For a property decision, talk to an environmental professional, or look up the site in the
          Missouri Department of Natural Resources and EPA databases.
        </li>
      </ul>

      <div className="info-grid">
        <section>
          <h2>Privacy</h2>
          <p>
            BlockHistory shows land uses from public historical maps. It doesn&apos;t show or
            collect anything about the people who own or live in a property, and it doesn&apos;t
            store the addresses you search. To find an address, the search is sent to the City of
            St. Louis address service (or, if it has no match, the US Census Bureau&apos;s). Visits are counted with Umami, which uses no
            cookies; it records how many searches found something, never the address.
          </p>
        </section>
        <section>
          <h2>Mistakes</h2>
          <p>
            If something is wrong, or you know what used to be at a place,{" "}
            <a href="https://github.com/Hariswar/BlockHistory/issues/new">tell us</a>.
          </p>
        </section>
      </div>
    </article>
  );
}
