# Filing Intelligence --- Codex Next Task

## Project Context

You are working on the **Filing Intelligence project**.

This project is a **personal AI sector financial research system**, not
a public SaaS product.

The goal is to improve:

-   research efficiency
-   explainability
-   peer comparison
-   trajectory intelligence
-   workflow automation

Not priorities:

-   UI polish
-   feature sprawl
-   large refactors

------------------------------------------------------------------------

# Current System Capabilities

The system already supports:

-   SEC filing ingestion
-   filing parsing
-   structured financial extraction
-   ratio metrics
-   growth metrics
-   signal generation
-   AI role classification
-   pairwise comparison
-   multi-company comparison
-   industry intelligence reports
-   strategic intelligence reports
-   visualization datasets
-   interactive Streamlit viewer

The viewer already includes:

-   scatter exploration
-   company filters
-   role filters
-   confidence filters
-   evidence preview
-   company detail panel
-   ecosystem structure table

The next improvements should focus on **research usability and
explainability**.

------------------------------------------------------------------------

# Development Roadmap (Immediate)

## Phase 1 --- Research Explainability

Improve the ability to inspect extraction evidence.

### Task: Evidence Drill-Down

Enhance the company detail panel so each metric can show full extraction
context.

For each metric display:

-   metric name
-   extracted value
-   confidence
-   warnings
-   filing section
-   source keyword
-   source snippet
-   raw match
-   unit

Requirements:

-   implement inside the current Streamlit viewer
-   keep existing filters and charts working
-   evidence must be expandable
-   do not redesign the entire viewer

Acceptance check:

select company\
expand metric\
see full extraction evidence\
confidence and warnings visible

------------------------------------------------------------------------

## Phase 2 --- Pairwise Viewer Mode

Enable direct company vs company comparison.

Add a **pairwise comparison viewer**.

User selects two companies.

Display comparison for:

-   revenue
-   operating_margin
-   net_margin
-   capex_ratio
-   revenue_growth
-   operating_income_growth
-   net_income_growth

Also display:

-   AI role classification
-   signals
-   confidence
-   warnings

Requirements:

-   reuse existing data structures
-   avoid duplicating extraction logic
-   implement as a simple viewer section or page

Acceptance check:

select company A\
select company B\
see head-to-head comparison

Examples:

MSFT vs NVDA\
NVDA vs AMD\
GOOGL vs META

------------------------------------------------------------------------

## Phase 3 --- Peer Position Context

Help understand where a company sits within the peer set.

Enhance the company detail panel.

Add simple ranking context:

-   revenue rank
-   profitability rank
-   growth rank
-   capex intensity rank

Implementation:

-   simple ordinal ranking
-   deterministic
-   handle missing data explicitly

Acceptance check:

click company\
see peer ranking context

------------------------------------------------------------------------

# Execution Order

Work sequentially.

1 Evidence Drill-Down\
2 Pairwise Viewer Mode\
3 Peer Position Context

Do not implement all at once.

Each feature should be:

-   small
-   safe
-   testable

------------------------------------------------------------------------

# Step 1 --- Repository Analysis

First analyze the repository.

Identify:

-   which files control the Streamlit viewer
-   which files implement the company detail panel
-   where evidence preview logic currently exists

Then propose:

Feature\
Files to modify\
Change summary\
Risk level

Keep changes minimal.

------------------------------------------------------------------------

# Constraints

Do NOT:

-   rewrite the whole viewer
-   refactor unrelated modules
-   change the data schema
-   break existing viewer functionality

Prefer:

-   additive changes
-   small patches
-   simple logic

------------------------------------------------------------------------

# Definition Of Success

Success means:

-   faster company research
-   deeper evidence inspection
-   clearer peer comparison
-   more trust in extraction outputs

Not success:

-   prettier UI
-   adding many widgets
-   large architectural rewrites
