# AGENTS.md

This document defines how AI coding agents should interact with the repository.

Agents must read this file before implementing code.

---

# Agent Role

AI agents act as implementation engineers.

The human architect defines:

- architecture
- project scope
- design philosophy

Agents must follow:

docs/ARCHITECTURE.md  
docs/AGENTS.md  
docs/CODING_GUIDELINES.md

---

# Core Workflow

Public Filing
→ Parsing
→ Signal Extraction
→ Insight Generation
→ Comparison Output

Agents must preserve this pipeline.

---

# Implementation Rules

1. Do not mix responsibilities across modules.
2. Parsing logic must remain separate from intelligence logic.
3. Extraction modules must produce structured outputs.
4. Do not add unnecessary frameworks.
5. Keep modules small and readable.

---

# Directory Responsibilities

config → project configuration  
ingestion → fetch filings  
parsing → parse documents  
extraction → extract signals  
intelligence → generate insights  
exporters → save outputs  

---

# Forbidden Actions

Agents should NOT:

- introduce new architecture layers
- rewrite entire modules without reason
- mix parsing and analysis logic
- implement trading algorithms

---

# Preferred Development Order

1 project skeleton  
2 watchlist  
3 ingestion  
4 parser  
5 section splitter  
6 financial extraction  
7 AI signal extraction  
8 insight generator  
9 comparison engine  
10 exporters

---

# Output Requirements

Each analysis must produce:

structured JSON  
markdown insight report  
comparison summary

---

# Error Handling

Parsing failures must not crash the pipeline.

Instead:

return diagnostics  
log section failures  
continue pipeline