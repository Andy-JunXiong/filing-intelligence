# Data Model

## FilingMetadata

company  
ticker  
filing_type  
filing_date  
source_url  

---

## ParsedFiling

metadata  
full_text  
sections

sections:

business  
mda  
risk_factors  
financials

---

## CompanySignal

company  
filing_date  

financial_metrics
- revenue
- operating_income
- net_income
- capex

ai_signals
- ai_mentions
- infrastructure_mentions

risk_signals
- regulatory
- competition
- supply_chain

narrative_signals
- growth_drivers
- outlook

---

## CompanyInsight

company  
filing_period  

key_changes  
ai_strategy_summary  
risk_summary  
watch_items  

---

## ComparisonReport

companies  
summary_table  
key_differences  
ranking