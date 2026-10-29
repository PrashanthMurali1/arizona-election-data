import { Link } from "react-router-dom";
export default function Methodology() {
  return (
    <article className="methodology">
      <h1>Data Sources &amp; Methodology</h1>
      <section>
        <h2>About This Project</h2>
        <p>
          Arizona Election Explorer is an independent, personal hobby and
          educational project built out of an interest in elections, political
          geography, data visualization, and software engineering.
        </p>
        <p>
          The goal is to make Arizona election information easier to access,
          explore, and understand through interactive maps, historical results,
          and early-voting participation statistics.
        </p>
        <p>
          Election data is often scattered across government websites, PDF
          documents, spreadsheets, and third-party datasets. This project aims
          to bring that information together in a more accessible format while
          preserving transparency about its sources, accuracy, and limitations.
        </p>
        <p>
          Beyond exploring Arizona's electoral history, the application also
          serves as a hands-on learning experience in software development, data
          engineering, visualization, and the challenges of working with
          real-world public datasets.
        </p>
        <p>
          <strong>
            This is not a commercial product or an official election information
            service.
          </strong>{" "}
          It is a project I develop and maintain independently in my spare time,
          both for personal interest and as an opportunity to learn, experiment,
          and improve my technical skills.
        </p>
        <p>
          Despite its informal nature, I aim to approach the underlying data
          carefully, prioritize official records whenever possible, and clearly
          distinguish verified results from preliminary or third-party
          information.
        </p>
        <p>
          The following sections explain how election data is collected,
          processed, validated, and displayed, along with the limitations
          visitors should be aware of.
        </p>
      </section>
      <section>
        <h2>Understanding the Data</h2>
        <p>
          Arizona Election Explorer is an independent, personal project
          dedicated to making Arizona election information easier to explore and
          understand.
        </p>
        <p>
          The platform brings together historical election results, geographic
          data, and early-voting participation statistics from publicly
          available sources. The goal is to present this information in a
          consistent, accessible format while remaining transparent about where
          the data comes from, how it is processed, and what it can—and
          cannot—tell us.
        </p>
        <p>
          Election data can vary considerably depending on the source, reporting
          period, and type of election. For that reason, the platform
          distinguishes between certified election results, historical records
          compiled from multiple sources, and preliminary participation reports.
        </p>
        <p>
          The sections below explain how this information is collected,
          validated, and displayed.
        </p>
      </section>
      <section>
        <h2>1. Historical Election Results</h2>
        <h3>Official Election Records</h3>
        <p>
          The primary source for historical Arizona election results is the{" "}
          <strong>Arizona Secretary of State</strong>, which publishes certified
          election canvasses containing the official results of statewide
          elections.
        </p>
        <p>
          These records provide candidate vote totals and, where available,
          county-level results, registration figures, ballots cast, and voter
          turnout.
        </p>
        <p>
          Whenever possible, the platform relies directly on certified election
          records rather than unofficial estimates or secondary reporting.
        </p>
        <p>
          Some elections require additional historical datasets to provide a
          complete county-level breakdown. When these sources are used, their
          figures are checked against the official statewide canvass.
        </p>
        <p>
          Original source documents are linked from the relevant election pages
          so visitors can independently review the published results.
        </p>
        <h3>Data Collection and Processing</h3>
        <p>
          Election records are not always published in a format that can be
          imported directly into a database.
        </p>
        <p>
          For example, some historical election results are available primarily
          as PDF documents, while others require combining records from multiple
          sources.
        </p>
        <p>
          To make these datasets suitable for interactive exploration, the
          information is organized into a consistent structure containing
          election details, candidates, geographic areas, vote totals, and
          available turnout statistics.
        </p>
        <p>
          For the 2014 and 2022 elections, reviewed transcriptions of official
          canvass tables were used after automated access to the source
          documents was blocked during development.
        </p>
        <p>
          The original documents remain linked, and the transcribed source
          tables and checksums are retained in the project repository for
          traceability.
        </p>
        <h3>Verifying Election Results</h3>
        <p>
          An important part of the data collection process is ensuring that the
          displayed results are consistent with official records.
        </p>
        <p>
          For elections containing county-level candidate results, the platform
          compares the sum of each candidate's votes across Arizona's 15
          counties against the corresponding statewide total published in the
          official canvass.
        </p>
        <p>A dataset is considered verified only when:</p>
        <ul>
          <li>
            Every candidate's county-level vote totals match the official
            statewide figures.
          </li>
          <li>No required county-level candidate results are missing.</li>
          <li>
            The resulting totals are consistent with the certified election
            records.
          </li>
        </ul>
        <p>
          This process helps identify transcription errors, missing records, and
          inconsistencies between sources.
        </p>
        <p>
          Verification means the imported data reconciles with the cited
          records. It does not represent an independent audit of the election
          itself.
        </p>
      </section>
      <section>
        <h2>2. Early-Voting Participation</h2>
        <h3>Understanding Early-Voting Reports</h3>
        <p>
          In addition to historical election results, Arizona Election Explorer
          displays early-voting participation statistics for the 2026 election
          cycle.
        </p>
        <p>
          These reports are obtained from <strong>civicAPI</strong>, a
          third-party election data provider, and include information about
          requested and returned early ballots.
        </p>
        <p>
          Where available, visitors can examine participation at both the
          statewide and county levels.
        </p>
        <p>
          Unlike historical election results, these figures describe
          participation in the voting process rather than the outcome of an
          election.
        </p>
        <h3>Participation Is Not Candidate Support</h3>
        <p>This is an important distinction.</p>
        <p>
          Early-voting reports may categorize participating voters by political
          party registration. However, a voter's registered party does not
          establish which candidate they supported.
        </p>
        <p>
          For example, a returned ballot associated with a registered Republican
          voter does not necessarily represent a vote for a Republican
          candidate. The same principle applies to Democratic and other
          registered voters.
        </p>
        <p>
          For this reason,{" "}
          <strong>
            early-voting participation figures should never be interpreted as
            candidate vote totals, election results, or election predictions.
          </strong>
        </p>
        <p>
          Where county maps use red or blue coloring for early-voting data,
          those colors indicate which party-registration category has the
          largest number of returned ballots:
        </p>
        <ul>
          <li>
            <strong>Blue:</strong> Democratic registrants have the largest
            returned-ballot count.
          </li>
          <li>
            <strong>Red:</strong> Republican registrants have the largest
            returned-ballot count.
          </li>
          <li>
            <strong>Gray:</strong> Another registration category leads,
            categories are tied, or sufficient data is unavailable.
          </li>
        </ul>
        <p>
          These visualizations reflect reported participation patterns only.
          They do not indicate how voters marked their ballots.
        </p>
        <h3>Reporting and Updates</h3>
        <p>
          Early-voting data is provided through source snapshots, which record
          the information available at a particular point in time.
        </p>
        <p>
          Each snapshot includes relevant reporting and retrieval dates,
          displayed using Arizona local time (America/Phoenix).
        </p>
        <p>
          The data is updated through manual refreshes rather than a continuous
          live feed. Consequently, the latest available snapshot may not reflect
          the most recent participation activity.
        </p>
        <p>
          The platform preserves the provider's reported categories and
          distinguishes between requested and returned ballots.
        </p>
        <p>
          Statewide figures use the statewide totals supplied by the provider
          rather than estimates created by adding county reports together.
        </p>
        <p>
          These records are attributed to civicAPI and are not presented as
          officially certified election results or independently verified
          participation totals.
        </p>
      </section>
      <section>
        <h2>3. Candidates, Vote Shares, and Write-In Votes</h2>
        <h3>Candidate Results</h3>
        <p>
          Historical election pages aim to preserve the candidate information
          published in their underlying sources.
        </p>
        <p>
          This includes named write-in candidates when they are individually
          identified in the election records.
        </p>
        <p>
          When a source reports write-in votes only as an aggregate category,
          those votes are not attributed to a particular candidate.
        </p>
        <p>
          This distinction helps prevent the presentation of unsupported
          candidate-level results.
        </p>
        <h3>Calculating Vote Percentages</h3>
        <p>
          Candidate vote shares are calculated using the total votes recorded
          for all verified candidates in the corresponding contest.
        </p>
        <p>The general calculation is:</p>
        <p>
          <strong>
            Candidate Vote Share = (Candidate Votes ÷ Total Contest Votes) × 100
          </strong>
        </p>
        <p>
          Percentages are displayed using appropriate rounding. Very small
          positive percentages below 0.01% are displayed as less than 0.01%
          rather than being rounded to zero.
        </p>
      </section>
      <section>
        <h2>4. Voter Turnout and Ballots Cast</h2>
        <p>
          Election results and voter turnout describe related but different
          aspects of an election.
        </p>
        <p>
          <strong>Candidate votes</strong> represent votes recorded for
          candidates in a specific contest.
        </p>
        <p>
          <strong>Ballots cast</strong> represent the ballots submitted by
          participating voters. A ballot may contain no valid vote for a
          particular contest, so ballots cast and candidate vote totals are not
          necessarily equal.
        </p>
        <p>
          <strong>Voter turnout</strong> expresses participation relative to the
          eligible registered electorate, according to the definition and
          calculation published by the election authority.
        </p>
        <p>
          Where official turnout figures are available, Arizona Election
          Explorer preserves those published values and their reported rounding
          rather than substituting an independently calculated rate.
        </p>
        <p>
          If the underlying source does not provide a particular turnout or
          registration statistic, that value is shown as unavailable.
        </p>
      </section>
      <section>
        <h2>5. Maps and Geographic Boundaries</h2>
        <h3>Arizona County Maps</h3>
        <p>
          County-level election results are visualized using geographic
          boundaries published by the <strong>U.S. Census Bureau</strong>.
        </p>
        <p>
          The platform uses the Census Bureau's 2022 cartographic county
          boundaries at a scale of 1:500,000.
        </p>
        <p>
          Election records are associated with the appropriate counties using
          their five-digit Census geographic identifiers (GEOIDs).
        </p>
        <p>
          Using a consistent set of county boundaries allows visitors to explore
          historical elections through a uniform geographic interface.
        </p>
        <p>
          These maps are intended for data visualization and do not represent a
          reconstruction of every historical electoral boundary.
        </p>
        <h3>Interpreting Map Colors</h3>
        <p>
          For historical election results, county colors generally reflect the
          candidate or party receiving the largest number of votes in that
          county.
        </p>
        <p>
          Counties with tied results, unavailable winning candidates, or winners
          outside the two major parties may be displayed using a neutral color.
        </p>
        <p>
          Colors provide a quick visual summary, but they do not convey the full
          distribution of votes.
        </p>
        <p>
          Visitors should consult the accompanying candidate totals, vote
          percentages, and county tables for a more complete understanding of
          the results.
        </p>
      </section>
      <section>
        <h2>6. U.S. House Elections</h2>
        <p>
          Congressional elections require a different geographic approach
          because Arizona is divided into congressional districts rather than
          statewide or countywide electoral contests.
        </p>
        <p>
          The platform displays individual U.S. House races using Census
          congressional district boundaries associated with the applicable
          redistricting plan.
        </p>
        <p>
          For elections beginning in 2012 or 2022, the corresponding district
          boundary plan is used.
        </p>
        <p>
          Because congressional boundaries change following redistricting,{" "}
          <strong>
            a district number does not necessarily describe the same geographic
            area across different election cycles.
          </strong>
        </p>
        <p>
          For example, comparing District 1 in two elections conducted under
          different redistricting plans may involve substantially different
          populations and geographic boundaries.
        </p>
        <h3>Historical Congressional Results</h3>
        <p>
          The platform includes regular U.S. House elections from 2014 through
          2024, covering Arizona's nine congressional districts in each
          election.
        </p>
        <p>
          These results are reconciled against official election statistics
          published by the Clerk of the U.S. House of Representatives.
        </p>
        <p>
          For Arizona's 2014 District 2 election, the final court-certified
          recount results take precedence over the original canvass figures.
        </p>
        <h3>Special Elections</h3>
        <p>
          Special elections are displayed separately from regular congressional
          elections.
        </p>
        <p>
          Because a special election concerns a particular vacant seat, only the
          district in which the election occurred is treated as contested. Other
          districts are identified as <em>Not contested</em>.
        </p>
        <p>
          The 2018 District 8 and 2025 District 7 special-election views use
          candidate reports provided by civicAPI. These are identified as
          third-party data rather than official canvass results.
        </p>
        <p>
          Write-in results, county-level allocations, and turnout figures are
          not displayed for these special-election datasets.
        </p>
      </section>
      <section>
        <h2>7. Additional Historical Data Sources</h2>
        <p>
          Some historical election datasets require information from multiple
          public sources to construct a complete record.
        </p>
        <p>The 2018 Arizona election is one example.</p>
        <p>Its county-level candidate results include information from:</p>
        <ul>
          <li>
            <strong>VEST:</strong> Precinct-level election records used to
            derive county totals for three ballot-listed candidates.
          </li>
          <li>
            <strong>OpenElections:</strong> County-level records used for five
            individually named write-in candidates.
          </li>
          <li>
            <strong>Arizona Secretary of State:</strong> The official statewide
            canvass used to reconcile all eight candidates' totals.
          </li>
        </ul>
        <p>
          The VEST dataset also contains a broader aggregate of 3,203 write-in
          votes. This figure is preserved for auditing purposes but is not
          combined with the 275 certified votes attributed to individually named
          write-in candidates.
        </p>
        <p>
          Official county-level registration figures, ballots cast, and turnout
          statistics are also available for this election.
        </p>
        <p>
          The use of multiple sources is documented to help visitors understand
          how the final historical dataset was assembled.
        </p>
      </section>
      <section>
        <h2>8. Missing, Incomplete, and Unavailable Data</h2>
        <p>Not all election records contain the same level of detail.</p>
        <p>
          Some datasets provide complete candidate results and turnout
          statistics, while others lack particular county-level values, write-in
          breakdowns, or participation metrics.
        </p>
        <p>
          Arizona Election Explorer distinguishes explicitly between a reported
          value of zero and a value that is unavailable.
        </p>
        <ul>
          <li>
            <strong>0:</strong> The source explicitly reports a value of zero.
          </li>
          <li>
            <strong>N/A:</strong> The information is unavailable or was not
            provided.
          </li>
          <li>
            <strong>Not contested:</strong> No election was held for that
            district or geographic area in the displayed contest.
          </li>
        </ul>
        <p>Missing values are never automatically treated as zero.</p>
        <p>
          When required candidate results are incomplete, the platform withholds
          derived winners, totals, and vote shares rather than displaying
          potentially misleading calculations.
        </p>
        <p>
          This approach prioritizes accurate representation of the underlying
          records over artificially complete visualizations.
        </p>
      </section>
      <section>
        <h2>9. Accuracy, Transparency, and Limitations</h2>
        <p>
          Arizona Election Explorer is designed to make election information
          easier to explore while preserving important distinctions between
          different types of data.
        </p>
        <p>
          Historical datasets may reflect official certified results, while
          newer participation reports may come from third-party providers and
          remain subject to updates, corrections, or reporting delays.
        </p>
        <p>
          Although efforts are made to validate the data against its cited
          sources, the platform may contain transcription errors, incomplete
          historical records, outdated snapshots, or other inaccuracies.
        </p>
        <p>
          Where possible, source documents and reporting dates are provided so
          visitors can independently evaluate the information.
        </p>
        <p>
          <strong>
            For authoritative election results, registration information, voting
            procedures, and election deadlines, always refer to the Arizona
            Secretary of State or the appropriate county election authority.
          </strong>
        </p>
      </section>
      <section>
        <h2>Independence &amp; Disclaimer</h2>
        <p>
          Arizona Election Explorer is a personal hobby and educational project.
          It is independently developed and is not affiliated with, endorsed by,
          or operated by any government agency, election authority, political
          party, or campaign.
        </p>
        <p>
          The information presented is intended for educational, informational,
          and exploratory purposes. Although care is taken to accurately
          represent publicly available election data, errors, omissions, and
          reporting delays may occur.
        </p>
        <p>
          For authoritative election results and official voting information,
          please consult the{" "}
          <a href="https://azsos.gov/elections">Arizona Secretary of State</a>{" "}
          or the appropriate county election authority.
        </p>
      </section>
      <Link className="text-link" to="/">
        ← Back to election catalog
      </Link>
    </article>
  );
}
