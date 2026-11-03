# 1928 registration and turnout correction

The prior raw record had only 13 numeric county registrations, with Yuma and the state left null. Five of those county values were also misread from a faded scan. The clearer Arizona Secretary of State registration-history table was used to correct Coconino (3,703), Maricopa (43,487), Navajo (3,834), Pinal (3,925), Yavapai (10,121), and fill Yuma (5,294).

Source: https://apps.azsos.gov/election/VoterReg/History/General/#1928
Official PDF: https://apps.azsos.gov/election/VoterReg/History/Year/1928.pdf

The sum of the 14 published county registrations is 119,728. The same official table prints a flagged statewide total of 119,528, a 200-person discrepancy. Both are retained in the raw record; the displayed statewide registration denominator is the derived county sum, with an explicit note. Presidential race participation is 91,254 / 119,728 = 76.22%.

The importer now derives missing statewide registration only when all counties have numeric registration totals. It never treats a partial county sum as complete.

RightDataUSA's 1928 page reports 39% statewide turnout and the same 91,254 presidential votes. Inspection of its returned HTML found its turnout tooltip explicitly describes an estimated percentage of the voting-age population. It therefore uses a different denominator from this application's registered-voter race participation.

RightDataUSA: https://www.rightdatausa.com/election_results?y=1928&t=P&r=N&s=AZ&d=00&WhichMap=vs
Turnout definitions: https://electionlab.mit.edu/research/voter-turnout
VEP methodology: https://election.lab.ufl.edu/voter-turnout/

No Superpowers workflow was used for this correction, as requested.

Verification: 28 backend historical/cache tests, 22 frontend unit tests, four browser regressions, and the frontend production build passed. The live 1928 statewide registration equals the sum of all 14 live county registrations; 119,728 and 76.22% are visible at desktop/mobile widths. The updated preview remains at http://127.0.0.1:5173/.
