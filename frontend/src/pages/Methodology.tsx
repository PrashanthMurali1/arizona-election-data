import { Link } from "react-router-dom";
export default function Methodology() {
  return (
    <article className="methodology">
      <p className="eyebrow">ABOUT THE ARCHIVE</p>
      <h1>
        The record behind
        <br />
        <span>the results.</span>
      </h1>
      <p className="lead">
        Election data should be traceable, understandable, and honest about
        what’s missing.
      </p>
      <section>
        <h2>Official sources, reconciled totals</h2>
        <p>
          Results come from the Arizona Secretary of State’s certified statewide
          canvasses. The importer compares each candidate’s sum across all 15
          counties with the separately published statewide total. A dataset is
          marked verified only when all candidate totals match and no county
          values are missing.
        </p>
        <p>
          2022 and 2014 use reviewed transcriptions of the official canvass
          tables. The source PDFs are linked on each election page. Direct
          automated downloads were blocked by the source server during
          development; the repository retains the transcribed source tables and
          their checksums.
        </p>
      </section>
      <section>
        <h2>2026 participation and reporting stages</h2>
        <p>
          The homepage’s Live Elections tab displays 2026 Early Voting using
          civicAPI early-voting participation reports. Requested and returned
          ballots appear statewide and by county, with the provider's party
          categories preserved. These categories describe participation, not
          candidate support. Missing metrics are N/A, while an explicit zero
          remains zero. Candidate results stay unavailable. Blue/red counties
          indicate the uniquely largest Democratic/Republican party-registration
          group among returned ballots. Other, tied or missing breakdowns remain
          gray. These colors do not show which candidates voters selected or how
          they voted.
        </p>
        <p>
          Source snapshots are refreshed manually and show their own reporting
          and retrieval dates in America/Phoenix. Previous releases and source
          corrections remain auditable. These 2026 records are attributed to the
          provider rather than described as official canvass results or
          independently verified data. Statewide totals use the supplied
          statewide party buckets; county totals are not added into a statewide
          estimate. Requested and returned categories are kept separate. No
          state/county corroboration or election-data reconciliation is
          performed.
        </p>
      </section>
      <section>
        <h2>Every reported candidate</h2>
        <p>
          Named write-in candidates retain their names and affiliations as
          published. Aggregate or unattributed write-ins, when present in a
          future source, are kept as categories rather than assigned to a
          person. Percentages use the sum of all verified candidate votes in the
          contest. Small positive shares below 0.01% are shown as &lt;0.01%.
        </p>
      </section>
      <section>
        <h2>Turnout is a different measure</h2>
        <p>
          Contest votes are votes recorded for candidates in this particular
          contest. Ballots cast include ballots with no valid vote in that
          contest. Official turnout uses total ballots cast divided by eligible
          voter registration, with the source’s reported rounding. The app
          preserves the published figures rather than calculating an alternative
          turnout rate.
        </p>
      </section>
      <section>
        <h2>Geography & missing data</h2>
        <p>
          The map uses official U.S. Census Bureau 2022 cartographic county
          boundaries at 1:500,000 scale. County results join through five-digit
          Census GEOIDs. This common boundary vintage is used for historical
          visualization; it does not imply a historical district map.
        </p>
        <p>
          N/A means unavailable. Missing values are never converted to zero.
          Winners, totals and vote shares are withheld for incomplete result
          sets. Counties with a tie, another-party winner or unavailable winner
          use a neutral map color. Read candidate and table labels alongside the
          colors.
        </p>
      </section>
      <section>
        <h2>U.S. House district results</h2>
        <p>
          House elections contain separate contests for each congressional
          district. Their maps use Census congressional boundaries for the plan
          first used in 2012 or 2022, as appropriate to the election. Selecting
          a district shows its own candidates and vote shares. District numbers
          across different plans do not identify the same geography.
        </p>
        <p>
          The six regular elections from 2014 through 2024 include all nine
          districts and reconcile with official House Clerk statistics. The
          final court-certified 2014 District 2 recount supersedes the original
          canvass. Special-election views cover only the contested district;
          other districts are labeled Not contested. The 2018 CD8 and 2025 CD7
          special views display civicAPI candidate reports and identify them as
          civicAPI data, not official canvass results. Write-in results,
          county-level allocations and special-election turnout are not shown.
        </p>
      </section>
      <section>
        <h2>Historical availability</h2>
        <p>
          The 2018 election includes all 15 counties and eight certified
          candidates. Three ballot candidates use VEST precinct sums; five named
          write-ins use OpenElections county records. Every candidate reconciles
          with the official statewide canvass. VEST’s broader aggregate of 3,203
          write-ins is retained for audit and excluded from the 275 certified
          named write-in votes. Official county registration, ballots and
          turnout are also available.
        </p>
      </section>
      <Link className="text-link" to="/">
        ← Back to election catalog
      </Link>
    </article>
  );
}
