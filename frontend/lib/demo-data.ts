import type {
  AnalysisReport,
  ClaimOut,
  ContradictionOut,
  DocumentItem,
} from "./medical-api";

export const DEMO_MODE =
  process.env.NEXT_PUBLIC_DEMO_MODE === "true" ||
  (typeof window !== "undefined" && !process.env.NEXT_PUBLIC_API_URL);

export const DEMO_DOCUMENTS: DocumentItem[] = [
  {
    id: 1,
    title: "Atorvastatin and Cardiovascular Mortality: A Randomized Controlled Trial",
    source_url: null,
    abstract:
      "RCT of 4,200 patients showing atorvastatin 40mg daily reduces cardiovascular mortality by 28% (HR 0.72, p<0.001) over 5 years.",
    created_at: "2026-06-10T08:00:00Z",
    updated_at: "2026-06-10T08:00:00Z",
  },
  {
    id: 2,
    title: "Statin Therapy and Cardiovascular Outcomes in Elderly Patients: A Retrospective Cohort Study",
    source_url: null,
    abstract:
      "Cohort study of 890 elderly patients (>75y) finding no cardiovascular benefit from atorvastatin (HR 1.12, p=0.33), with increased myopathy and falls.",
    created_at: "2026-06-10T09:00:00Z",
    updated_at: "2026-06-10T09:00:00Z",
  },
  {
    id: 3,
    title: "Metformin for Type 2 Diabetes: A Systematic Review and Meta-Analysis",
    source_url: null,
    abstract:
      "Meta-analysis of 18 RCTs (n=12,000) demonstrating metformin reduces HbA1c by 1.12% and cardiovascular mortality by 22%.",
    created_at: "2026-06-10T10:00:00Z",
    updated_at: "2026-06-10T10:00:00Z",
  },
];

const CLAIMS: ClaimOut[] = [
  {
    id: 1,
    document_id: 1,
    chunk_index: 0,
    drug: "atorvastatin",
    condition: "hypercholesterolemia",
    outcome: "cardiovascular mortality",
    direction: "positive",
    population: "Adults 45-75 with LDL >130 mg/dL",
    study_type: "rct",
    sample_size: 4200,
    effect_size: "HR 0.72 (95% CI 0.61-0.85)",
    confidence: 0.95,
    raw_text:
      "Atorvastatin significantly reduced cardiovascular mortality compared to placebo (HR 0.72, 95% CI 0.61-0.85, p<0.001). The treatment group showed a 28% relative risk reduction in cardiovascular death.",
    grade_score: 4,
    evidence_label: "RCT",
  },
  {
    id: 2,
    document_id: 1,
    chunk_index: 0,
    drug: "atorvastatin",
    condition: "hypercholesterolemia",
    outcome: "all-cause mortality",
    direction: "positive",
    population: "Adults 45-75 with LDL >130 mg/dL",
    study_type: "rct",
    sample_size: 4200,
    effect_size: "HR 0.85 (95% CI 0.74-0.97)",
    confidence: 0.88,
    raw_text:
      "All-cause mortality was also reduced (HR 0.85, 95% CI 0.74-0.97).",
    grade_score: 4,
    evidence_label: "RCT",
  },
  {
    id: 3,
    document_id: 2,
    chunk_index: 0,
    drug: "atorvastatin",
    condition: "hypercholesterolemia",
    outcome: "cardiovascular mortality",
    direction: "negative",
    population: "Elderly patients >75 years",
    study_type: "cohort",
    sample_size: 890,
    effect_size: "HR 1.12 (95% CI 0.89-1.41)",
    confidence: 0.82,
    raw_text:
      "Atorvastatin use was not associated with reduced cardiovascular mortality in this elderly cohort (HR 1.12, 95% CI 0.89-1.41, p=0.33). There was a trend toward increased all-cause mortality in the statin group.",
    grade_score: 3,
    evidence_label: "Cohort",
  },
  {
    id: 4,
    document_id: 2,
    chunk_index: 0,
    drug: "atorvastatin",
    condition: "hypercholesterolemia",
    outcome: "myopathy",
    direction: "negative",
    population: "Elderly patients >75 years",
    study_type: "cohort",
    sample_size: 890,
    effect_size: "12.4% vs 3.1%, p<0.001",
    confidence: 0.91,
    raw_text:
      "The statin group experienced significantly higher rates of myopathy (12.4% vs 3.1%, p<0.001) and new-onset diabetes (8.7% vs 5.2%, p=0.02).",
    grade_score: 3,
    evidence_label: "Cohort",
  },
  {
    id: 5,
    document_id: 3,
    chunk_index: 0,
    drug: "metformin",
    condition: "type 2 diabetes",
    outcome: "HbA1c reduction",
    direction: "positive",
    population: "Type 2 diabetes patients",
    study_type: "meta_analysis",
    sample_size: 12000,
    effect_size: "WMD -1.12% (95% CI -1.35 to -0.89)",
    confidence: 0.96,
    raw_text:
      "Metformin treatment was associated with significant reduction in HbA1c (weighted mean difference -1.12%, 95% CI -1.35 to -0.89, p<0.001) compared to placebo across 18 trials.",
    grade_score: 5,
    evidence_label: "Meta-analysis",
  },
  {
    id: 6,
    document_id: 3,
    chunk_index: 0,
    drug: "metformin",
    condition: "type 2 diabetes",
    outcome: "cardiovascular mortality",
    direction: "positive",
    population: "Type 2 diabetes patients",
    study_type: "meta_analysis",
    sample_size: 12000,
    effect_size: "RR 0.78 (95% CI 0.68-0.89)",
    confidence: 0.93,
    raw_text:
      "Cardiovascular mortality was reduced by 22% (pooled RR 0.78, 95% CI 0.68-0.89, p<0.001).",
    grade_score: 5,
    evidence_label: "Meta-analysis",
  },
];

const CONTRADICTIONS: ContradictionOut[] = [
  {
    id: 1,
    claim_a: CLAIMS[0],
    claim_b: CLAIMS[2],
    contradiction_type: "DIRECT",
    severity: "HIGH",
    explanation:
      "These studies reach opposing conclusions about atorvastatin's effect on cardiovascular mortality. The RCT (n=4,200, ages 45-75) found a significant 28% reduction (HR 0.72), while the cohort study (n=890, ages >75) found no benefit and a non-significant trend toward harm (HR 1.12). The conflict likely reflects population differences: the RCT enrolled middle-aged adults with moderate risk, while the cohort studied elderly patients with higher comorbidity burden and competing mortality risks. The RCT provides stronger causal evidence (Grade 4 vs 3), but its findings may not generalize to elderly populations.",
    consensus:
      "The weight of evidence supports atorvastatin for cardiovascular mortality reduction in adults aged 45-75 (RCT, Grade 4, n=4,200). However, benefit in patients over 75 is unproven, with one cohort study suggesting potential harm. Current evidence supports age-stratified prescribing: strong recommendation for middle-aged patients, cautious individual assessment for elderly patients weighing falls, myopathy risk, and limited life expectancy.",
  },
  {
    id: 2,
    claim_a: CLAIMS[0],
    claim_b: CLAIMS[3],
    contradiction_type: "METHODOLOGICAL",
    severity: "MEDIUM",
    explanation:
      "While Study 1 reports atorvastatin as safe with similar adverse events between groups (myalgia 8.2% vs 7.1%), Study 2 found significantly elevated myopathy rates (12.4% vs 3.1%) in elderly patients. This methodological contradiction arises from different study designs (RCT vs retrospective cohort), different populations (middle-aged vs elderly), and different myopathy definitions and ascertainment methods.",
    consensus:
      "Atorvastatin safety varies significantly by age group. In middle-aged adults (RCT evidence), myalgia rates are modest and comparable to placebo. In elderly patients >75, myopathy risk is substantially elevated (cohort evidence), compounded by falls risk. Clinicians should monitor elderly patients more closely and consider lower starting doses.",
  },
];

export const DEMO_REPORT: AnalysisReport = {
  job_id: "demo-00000000-0000-0000-0000-000000000000",
  document_ids: [1, 2, 3],
  total_claims: CLAIMS.length,
  total_contradictions: CONTRADICTIONS.length,
  contradictions: CONTRADICTIONS,
};
