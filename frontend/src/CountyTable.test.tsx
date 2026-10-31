import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import CountyTable from "./CountyTable";
import type { Results } from "./types";
import {sortCounties} from "./results";

it("shows Republican and Libertarian shares when there is no Democratic candidate", () => {
  const row = {geoid:"04001",name:"Apache",status:"verified",total_votes:100,
    candidates:[{id:"a",name:"Woods",party:"REP",votes:80,write_in:false},
    {id:"b",name:"Karow",party:"LBT",votes:20,write_in:false}],winner:null,
    turnout:{percent:55.89}} as Results;
  const html=renderToStaticMarkup(<CountyTable counties={[row]} selected={null} onSelect={()=>{}} />);
  expect(html).toContain("Lbt %");
  expect(html).toContain("Rep %");
  expect(html).not.toContain("Dem %");
  expect(html).toContain("20.00%");
  expect(html).toContain("80.00%");
  expect(html).toContain("55.89%");
  const other = {...row,geoid:"04003",name:"Cochise",candidates:row.candidates.map(c=>({...c,votes:c.party==='LBT'?40:60}))};
  expect(sortCounties([row,other],'party:LBT','desc').map(r=>r.name)).toEqual(['Cochise','Apache']);
});
