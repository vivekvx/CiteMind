EXTRACTION_PROMPT = """Extract medical claims from the text below. Return JSON with key "claims" containing an array.

Each claim object must have these exact keys:
- drug: medication, treatment, or intervention name (string)
- condition: disease or medical condition (string)
- outcome: what was measured e.g. mortality, HbA1c, blood pressure (string)
- direction: "positive" (beneficial), "negative" (harmful), "neutral", or "unclear"
- population: patient group description, or null
- study_type: exactly one of: meta_analysis, rct, cohort, case_control, case_series, unknown
- sample_size: number of participants as integer, or null
- effect_size: brief effect description e.g. "HR 0.82 (0.71-0.94)", or null
- confidence: 0.0 to 1.0 how confident this is a real medical claim
- raw_text: exact sentence(s) from the text supporting this claim

Rules:
- Only extract claims with actual evidence (not background statements)
- direction must be exactly one of the four values above
- If no medical claims found, return {{"claims": []}}
- Return only valid JSON, no other text

Text:
{chunk_text}"""

EXPLANATION_PROMPT = """You are a medical research analyst. Two studies have contradictory findings about the same drug-condition-outcome combination.

Claim A ({study_type_a}, n={sample_size_a}):
"{raw_text_a}"
Direction: {direction_a}

Claim B ({study_type_b}, n={sample_size_b}):
"{raw_text_b}"
Direction: {direction_b}

Explain why these studies may have reached different conclusions. Consider:
- Differences in study design and methodology
- Population differences
- Dosing, duration, or outcome measurement differences
- Potential confounders or biases

Be concise (3-5 sentences). Use plain language accessible to clinicians."""

CONSENSUS_PROMPT = """You are a medical research analyst. Given these claims about {drug} and {condition}, synthesize the current evidence into a consensus statement.

Claims:
{claims_text}

Write a brief consensus statement (2-3 sentences) that:
- Weighs higher-evidence studies more heavily
- Acknowledges conflicting findings
- States the balance of evidence direction
- Notes key caveats

Use plain clinical language."""
