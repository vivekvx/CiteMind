# Product

## Register

product

## Users

Medical researchers, clinicians, and evidence-synthesis teams comparing findings across clinical papers. Secondary audience: technical reviewers and hiring managers evaluating the project as a portfolio piece. Users arrive with 2+ papers and want to know where the literature disagrees and which side the evidence favors.

## Product Purpose

CiteMind detects contradictions across medical literature. It extracts structured claims from uploaded papers, grades evidence quality on the GRADE hierarchy, pairs conflicting claims, and generates clinician-readable explanations and consensus statements. Success: a visitor lands, runs the demo analysis, and immediately understands what the pipeline does and trusts its output.

## Brand Personality

Precise, calm, evidence-first. The interface should feel like a serious clinical instrument, not a flashy SaaS landing. Confidence through clarity and typographic discipline, never through decoration.

## Anti-references

- Generic AI-generated Tailwind dark dashboards (uniform `border-white/[0.08]` cards, flat hierarchy, no motion)
- Crypto/SaaS gradient-heavy landing pages
- Medical-stock-photo corporate health sites

Reference for typographic discipline: Cal.com (display/body font split, negative letter-spacing on headlines, hierarchical radii, restrained monochrome palette) — adapted to our dark theme, not their white canvas.

## Design Principles

1. Evidence first: data (grades, sample sizes, effect sizes) is the visual hero, not chrome.
2. Hierarchy through type scale and weight, not boxes — fewer cards, stronger typography.
3. Motion explains: animations communicate pipeline progress and reveal results; never decorative bounce.
4. Dark, clinical calm: near-black canvas, restrained accent use; severity colors (red/amber) are the only loud voices.
5. Every state designed: loading, empty, and error states get the same care as the happy path.

## Accessibility & Inclusion

WCAG AA contrast (4.5:1 body text). `prefers-reduced-motion` honored on all animations. Severity never conveyed by color alone (always paired with text labels). Keyboard-focus visible on all interactive elements.
