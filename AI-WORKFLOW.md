# Engineering Workflow & AI Tooling

## How this assignment was built

This project was designed and built by **Aditya Pichikala** as a take-home engineering submission.

---

## AI Tools Used and How

| Tool | Used For |
|------|----------|
| **Antigravity (Google DeepMind)** | Primary coding assistant throughout — used for architecture planning, code scaffolding, debugging, and document drafting |
| **AI-assisted diagramming** | The Mermaid flowchart in `ARCHITECTURE.md` — drafted with AI tooling |

---

## What I Delegated vs. Wrote Myself

### Delegated to AI (with heavy review)
- **Initial boilerplate** — FastAPI app structure, Pydantic model scaffolding, SQLAlchemy schema skeletons. AI produced correct structure; I verified field types, constraints, and the reasoning in the docstrings.
- **Test boilerplate** — The `pytest` fixture setup and parametrize patterns. I wrote the test logic and assertions myself; AI helped with the file structure.
- **CSS styling** — `index.css` dark-mode design system. AI produced the color tokens and layout; I made all product decisions about what to show, what to hide, and what the hierarchy should be.
- **Docker configuration** — `Dockerfile` and `docker-compose.yml` structure. Standard patterns; AI got these right on the first try.
- **The Mermaid diagram** — Drafted with AI tooling. Every component it references is real and built.

### Written and reasoned through by me directly
- **`topology_builder.py`** — The core MST algorithm (`_build_inferred_topology`). I designed the greedy nearest-parent-towards-root approach after reasoning about why Kruskal's MST wouldn't work for radial LT lines. The algorithm is mine.
- **`localization_engine.py`** — The entire fault localization logic: boundary detection, dead sensor filter, subtree collection, scheduled outage suppression with 40-minute overrun. I worked through each case from the physics of the network.
- **`ingest_engine.py`** — The sequence-number deduplication logic and firmware 1.2.x watchdog. The key insight (use `seq` not `ts`) is mine; I had to explain it to AI before it could scaffold the code correctly.
- **All test cases** — Every test scenario (`test_topology.py`, `test_localization.py`, `test_ingest.py`, `test_lifecycle.py`) was designed by me. The test logic and assertions encode domain knowledge about what correct behaviour looks like.
- **All product decisions** — What to show on the operator console, what to leave off, why no map, why no LLM for localization, the confidence rating scheme, the 40-minute overrun buffer — these are my decisions, not AI suggestions.
- **All documentation** — `ARCHITECTURE.md`, `DECISIONS.md`, `DEPLOYMENT.md` prose. AI reviewed and suggested improvements; the reasoning is mine.

---

## Roughly How Much Code Is AI-Generated

Approximately **35–40%** of the final lines of code were AI-generated with minimal modification (boilerplate, styling, Docker config, test file structure). The remaining **60–65%** — the domain logic, the algorithm implementations, the test assertions, and all the product reasoning — was written by me, even when AI helped with syntax.

The more important number: **0% of the logic I can't explain**. Every function, every conditional, every design trade-off in this repo I can walk through line by line.

---

## Three Concrete Cases Where AI Was Wrong or Misleading

### Case 1 — AI overwrote acknowledged incident status on every poll

**What happened:** When scaffolding `run_localization_eval()`, AI wrote a simple loop that did `incidents_db[inc.incident_id] = inc` for every detected incident. This looked correct. But when the UI polled `GET /api/v1/incidents` every 3 seconds, it called `run_localization_eval()` which re-detected all active incidents and blindly overwrote the DB entries — resetting `ACKNOWLEDGED` status back to `DETECTED` every 3 seconds. Acknowledging a ticket was completely useless.

**How I caught it:** Live testing. I clicked "Acknowledge" on an incident, watched the status change for 2 seconds, then watched it flip back to DETECTED on the next poll. AI had not considered that the same incident could already be in the DB with a more advanced status.

**Fix:** Added a status-preservation guard:
```python
if inc.incident_id in incidents_db:
    inc.status = incidents_db[inc.incident_id].status
```

---

### Case 2 — AI used emoji in a print() statement that crashed Windows terminals

**What happened:** In the startup lifespan function, AI wrote:
```python
print(f"✅ Seeding Complete: {len(dts)} DTs, {len(poles)} Poles, {len(trees)} Trees loaded.")
```
This looks fine and works on macOS/Linux terminals. On Windows, the default terminal encoding is `cp1252`, which cannot encode the `✅` Unicode character. The entire backend crashed at startup with `UnicodeEncodeError`.

**How I caught it:** Trying to start the backend on Windows for the first time after development on a different machine. The server exited immediately with a traceback pointing to `cp1252.py`.

**Fix:** Replaced emoji with ASCII: `[OK] Seeding Complete: ...`

**Lesson:** AI develops and tests in a mental model of a Unix terminal with UTF-8. It does not consider Windows encoding constraints unless explicitly told to.

---

### Case 3 — AI initially suggested Kruskal's MST for missing topology

**What happened:** When I described the 60% missing topology problem, AI's first suggestion was to use Kruskal's algorithm to build a Minimum Spanning Tree from the pole GPS coordinates. It produced correct, working code. I implemented it, ran it against a test network, and immediately saw the problem: Kruskal's optimises for globally minimum total edge weight — it produces the most compact tree geometrically, not a radially-structured tree rooted at the DT. The result was a tree that looked like a spider web: poles connected to the closest other poles in all directions, with no directionality from DT outward.

This would cause the localization algorithm to produce wrong fault boundaries because the parent/child relationships didn't correspond to actual power flow direction.

**How I caught it:** Drawing the output tree on paper and asking: "would electricity actually flow through this structure from DT to house?" It wouldn't.

**Fix:** I designed the greedy nearest-parent-towards-root algorithm myself — sort by distance from DT, connect each pole to the nearest already-connected pole that is strictly closer to the DT. This enforces the radial, directional shape of real LT lines. AI then helped scaffold this once I explained the approach.

---

## The Prompts I Consider My Best Work

### Prompt 1 — Debugging the deduplication edge case

After spotting the acknowledged-status-overwrite bug, I used this prompt:
> *"In run_localization_eval(), every time this runs it calls localization_engine.localize() which returns fresh IncidentOutput objects. These are then written to incidents_db, overwriting any existing entry including its status field. An operator can acknowledge a ticket but the next poll will reset it to DETECTED. What is the minimal correct fix that preserves lifecycle status while still updating affected_pole_count and other detection fields?"*

This prompt is good because it diagnoses the exact root cause, states the invariant that must be preserved (lifecycle status), and asks for a minimal targeted fix rather than a redesign.

### Prompt 2 — Topology inference design

After rejecting Kruskal's, I used:
> *"I need to build a tree topology for LT distribution poles where I only have GPS coordinates and the DT location. The physical network is radial — all power flows outward from the DT. The tree must be rooted at the DT and all edges must be directed away from it. Kruskal's MST doesn't work because it doesn't enforce directionality. Design an algorithm that: (1) produces a rooted tree, (2) connects each pole to a parent that is electrically upstream (closer to DT), (3) handles spurs and branches naturally, (4) caps max span distance at 250m."*

This prompt is good because it specifies the physical constraint (directionality) that generic MST algorithms don't satisfy, and gives the algorithm its correctness criteria before asking for implementation.
