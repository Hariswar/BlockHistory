export const metadata = { title: "About & limits · BlockHistory" };

export default function About() {
  return (
    <article className="prose">
      <h1>About BlockHistory, and what it can&apos;t tell you</h1>
      <p>
        Fire insurance companies mapped American cities building by building. The Sanborn maps show
        what each building was used for, what it was made of, and where gasoline tanks were buried.
        BlockHistory reads those maps for Carondelet, St. Louis, and lists past uses near an address
        that sometimes left soil or groundwater contamination.
      </p>

      <h2>What&apos;s covered today</h2>
      <ul>
        <li>One map year: 1938 (Sanborn St. Louis Vol. 12).</li>
        <li>
          Two map sheets so far (47 and 56, along S. Broadway between Kraus and Steins). All 74
          sheets of the volume have been read; the others go on the map as they are matched to
          today&apos;s streets.
        </li>
        <li>No records yet for the years after 1938. The 1950 update is next.</li>
      </ul>

      <h2>How it works</h2>
      <ol>
        <li>The map scans come from the Library of Congress.</li>
        <li>
          An AI model (Claude Haiku) reads each part of each sheet: the business labels and the
          gasoline-tank symbols. A second look at full resolution counts the tanks.
        </li>
        <li>
          Each sheet is matched to today&apos;s streets using intersections from OpenStreetMap
          (typically within 1–3 m).
        </li>
        <li>People check the findings against the map; each result says whether it was checked.</li>
      </ol>

      <h2>How accurate it is</h2>
      <p>Measured on 10 sheets that were labeled by hand (119 sites):</p>
      <table>
        <tbody>
          <tr>
            <th>Labeled sites the AI found</th>
            <td>87%</td>
          </tr>
          <tr>
            <th>Flags that are real sites</th>
            <td>88%</td>
          </tr>
          <tr>
            <th>Gasoline-tank sites found</th>
            <td>14 of 15</td>
          </tr>
        </tbody>
      </table>
      <p>
        So some listings are wrong and some past uses are missing. Every listing links to the map
        image so you can check it yourself.
      </p>

      <h2>Limits</h2>
      <ul>
        <li>
          <strong>This is not an environmental site assessment.</strong> A past use doesn&apos;t
          mean the soil is contaminated today, and no listing doesn&apos;t mean it&apos;s clean.
        </li>
        <li>One year only: businesses that opened and closed between map years don&apos;t show.</li>
        <li>Address positions come from the US Census and can be 30–80 m off.</li>
        <li>
          For a property decision, talk to an environmental professional, or look up the site in the
          Missouri Department of Natural Resources and EPA databases.
        </li>
      </ul>

      <h2>Privacy</h2>
      <p>
        BlockHistory shows land uses from public historical maps. It doesn&apos;t show or collect
        anything about the people who own or live in a property, and it doesn&apos;t store the
        addresses you search. To find an address on the map, the search is sent to the US Census
        Bureau&apos;s free address lookup.
      </p>

      <h2>Mistakes</h2>
      <p>
        If something is wrong, or you know what used to be at a place,{" "}
        <a href="https://github.com/Hariswar/BlockHistory/issues/new">tell us</a>.
      </p>
    </article>
  );
}
