# Filing Intelligence — System Architecture

## Overview

Filing Intelligence is an AI-driven system designed to extract structured signals from public company filings.

The goal is to convert unstructured filings (10-K, 10-Q) into structured intelligence for research and quantitative analysis.

This system focuses on large-cap technology and AI companies.

Initial companies:

- Microsoft
- NVIDIA
- Alphabet
- Amazon

---

# Architecture Layers

## 1. Ingestion Layer

Purpose:
Download public filings.

Responsibilities:
- maintain company watchlist
- fetch filings
- store raw documents

Output:
raw filing files

Directory:
app/ingestion/

---

## 2. Parsing Layer

Purpose:
Convert raw filing into structured text.

Responsibilities:

- clean HTML/text
- normalize encoding
- split into sections

Key Sections:

- Business
- MD&A
- Risk Factors
- Financial Statements

Directory:
app/parsing/

---

## 3. Extraction Layer

Purpose:
Extract signals from sections.

Signal Types:

Financial Metrics
- revenue
- operating income
- net income
- capex

AI Strategy Signals
- AI mentions
- infrastructure investments
- model ecosystem references

Risk Signals
- regulatory risk
- competition risk
- supply chain risk

Management Narrative
- growth drivers
- outlook commentary

Directory:
app/extraction/

---

## 4. Intelligence Layer

Purpose:
Transform signals into research insights.

Outputs:

Company Insight
- key changes
- AI strategy summary
- risk summary

Cross Company Comparison
- AI investment intensity
- strategic positioning
- risk exposure

Directory:
app/intelligence/

---

## 5. Output Layer

Purpose:
Export analysis results.

Formats:

- JSON
- Markdown
- future dashboard

Directory:
app/exporters/

---

# Data Flow

watchlist  
↓  
filing fetch  
↓  
raw storage  
↓  
parse filing  
↓  
split sections  
↓  
extract signals  
↓  
generate insights  
↓  
export results

---

# v1 Scope

Included:

- SEC filing ingestion
- signal extraction
- insight generation

Excluded:

- trading strategies
- portfolio optimization
- market prediction