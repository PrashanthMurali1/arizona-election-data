# Arizona Election Explorer

For public-source privacy checks, local commit guards and safe handling of audit
reports, see [repository privacy](docs/repository-privacy.md).

**An interactive platform for exploring Arizona election results, historical voting trends, and early-voting participation.**

🌐 **Live website:** https://azelections.app/

## About the Project

Arizona Election Explorer is an independent, personal hobby project built out of an interest in elections, political geography, data visualization, and software engineering.

The goal is to make Arizona election data easier to access, explore, and understand through a modern, interactive interface.

Election information is often scattered across government websites, spreadsheets, PDF reports, and other sources. While this information is publicly available, it isn't always presented in a way that makes historical comparisons or geographic patterns easy to explore.

Arizona Election Explorer aims to bring that information together in one place, allowing visitors to examine election results, compare voting patterns across counties, and follow early-voting participation.

This is an ongoing personal project that I develop and maintain in my spare time. It is also an opportunity for me to experiment with new technologies, software architecture, data processing, and visualization techniques.

## Features

### Historical Election Results

Explore historical Arizona elections through an interactive dashboard.

- View statewide election results and candidate vote shares.
- Examine results across Arizona's 15 counties.
- Explore geographic voting patterns using interactive election maps.
- Compare candidate performance across counties.
- Navigate between available elections and election years.
- Access supporting election data and source information.

### Interactive County Maps

Election results are presented geographically to make voting patterns easier to understand.

- County-level maps visualize election outcomes.
- Interactive county selection provides additional details.
- Color-coded results help identify geographic voting patterns.
- County-level tables complement the map visualizations.

### Early Voting Tracker

Follow early-voting participation in Arizona using publicly available election data.

- View statewide early-voting participation.
- Explore participation across individual counties.
- Examine available early-voting statistics and trends.
- Track how participation changes as new data becomes available.

**Important:** Early-voting participation statistics do not indicate which candidate received a voter's ballot. Participation data should not be interpreted as actual election results or candidate support.

### Data Transparency

Making election information understandable also means making its origins clear.

The project emphasizes:

- Publicly available election data.
- Links to original sources where available.
- Clear distinctions between reported results and other election statistics.
- Transparent presentation of incomplete or unavailable data.
- Consistent presentation of statewide and county-level results.

## Technology Stack

Arizona Election Explorer is built using a modern web application architecture.

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Database migrations | Alembic |
| Containerization | Docker |
| Version control | Git and GitHub |

The application separates its frontend, backend, and data storage responsibilities to keep the codebase maintainable and extensible.

The project also serves as a practical environment for experimenting with deployment automation, caching, observability, and infrastructure management.

## Data Sources

Arizona Election Explorer uses publicly available election information, with an emphasis on official sources whenever possible.

An important reference is the **Arizona Secretary of State**, which publishes statewide election results, historical election information, and election-related statistics.

- [Arizona Secretary of State — Elections](https://azsos.gov/elections)
- [Arizona Secretary of State — Election Information](https://azsos.gov/elections/election-information)

Additional sources may be used for particular elections or datasets. Source references are provided within the application where available.

The project does not independently administer elections, count ballots, or certify election results.

## Project Status

**Active development — personal hobby project**

Arizona Election Explorer is an evolving application rather than a finished product.

I continue to improve the interface, expand historical data coverage, refine existing features, and experiment with new capabilities as time permits.

Areas of ongoing interest include:

- Expanding coverage of historical Arizona elections.
- Improving interactive maps and election visualizations.
- Making comparisons between election years easier.
- Enhancing early-voting data exploration.
- Improving application performance and caching.
- Building more reliable data ingestion and deployment workflows.
- Exploring statistical analysis of historical election trends.

These are areas of interest rather than commitments to a particular release schedule.

## Why I Built This

I've always been interested in understanding how elections evolve over time, especially the differences in voting behavior between geographic regions.

Arizona is particularly interesting because of its competitive statewide elections, changing electorate, and the substantial differences in voting patterns between its counties.

I wanted an easier way to explore those patterns without repeatedly digging through separate reports and spreadsheets.

As a software engineer, I also wanted a project where I could experiment freely with technologies and architectural decisions, and build something useful along the way.

This project brings those interests together.

There is no company or organization behind Arizona Election Explorer. It's simply something I enjoy building and improving.

## Feedback and Contributions

Feedback, bug reports, and suggestions are welcome.

If you notice incorrect election data, encounter a technical issue, or have an idea for improving the application, please open an issue in this repository.

Since this is a personal hobby project, development and maintenance happen in my spare time, and response times may vary.

## Disclaimer

**Arizona Election Explorer is an independent, unofficial project.**

It is not affiliated with, endorsed by, or operated by the Arizona Secretary of State, any county election department, or any other government agency.

Although care is taken to present accurate information from publicly available sources, errors, omissions, and delays may occur.

For official election results, voter information, deadlines, and election procedures, always consult the relevant government election authority.

Election data presented here is provided for informational and educational purposes only.

---

**Arizona Election Explorer** · Built as a personal hobby project.

[Explore the website](https://azelections.app/)
