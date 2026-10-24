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
          Three years only: businesses that opened and closed between 1908 and 1938, between 1938
          and 1950, or after 1950, don&apos;t show. &ldquo;Not on the 1950 map&rdquo; can also mean
          the reader missed it. The 1908 map is placed from street corners that still exist, so a
          few riverfront and Patch sheets are less precise.
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
          <p>
            If you send a note, we keep what you wrote, the decade and &ldquo;how you know&rdquo;
            you picked, the listing it&apos;s about (for corrections), the time, and the map
            point rounded to about 10 m. Not the address you searched, your name, contact details or
            IP address. Notes are read before anything is shown; only a shortened wording of
            approved memories appears on the site, marked as shared by a neighbor.
          </p>
        </section>
        <section>
          <h2>Mistakes</h2>
          <p>
            Each listing has a &ldquo;Something wrong with this listing?&rdquo; form, and every
            search ends with &ldquo;Remember what used to be here?&rdquo;. Corrections are checked
            against the map scan; memories help fill the years after 1950 that the maps don&apos;t
            cover. For problems with the website itself,{" "}
            <a href="https://github.com/Hariswar/BlockHistory/issues/new">report them on GitHub</a>.
          </p>
        </section>
      </div>
    </article>
  );
}
