export default function EarlyVotingSources() {
  return (
    <section
      className="sources source-section participation-sources"
      aria-labelledby="participation-sources-title"
    >
      <h4 id="participation-sources-title">Sources & coverage</h4>
      <p className="source-attribution">
        Participation reports from{" "}
        <a
          href="https://civicapi.org/early-vote/"
          target="_blank"
          rel="noreferrer"
        >
          civicAPI
        </a>
        , which collects counts from state election offices.
      </p>
    </section>
  );
}
