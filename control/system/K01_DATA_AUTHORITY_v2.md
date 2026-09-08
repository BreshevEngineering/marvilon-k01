# K01 Data Authority v2

There is no single absolute source of truth for the whole project.

- **Master** owns requirements, material/lifecycle status, OPEN gates and product identity.
- **Native SOLIDWORKS stable CAD** owns exact topology, feature tree, local geometry and actual assembly mate references.
- **Controlled parameter registry** owns shared design variables and equations.
- **CAD readback** proves native CAD matches controlled values.
- **BOM** is generated, never hand-authoritative.
- **Calculation reports** own solver evidence.
- **Technology registry** owns manufacturing route and process controls.
- **Decision records (EDRs)** own rationale, alternatives and why a solution was selected/rejected.
- **Release package** freezes all domains together at a controlled revision.

One numeric parameter shall not have two independent editable owners.
