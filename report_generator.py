"""
=============================================================
  Vendor Secure Integration Design Agent  —  Phase 3
  Security Design Document Generator
=============================================================

What this script does:
  1. Reads the JSON file produced by Phase 2 (risk_classifier.py)
  2. Sends the full risk assessment to Claude
  3. Claude generates a structured Security Design Document in Markdown
  4. The document is saved as a .md file and printed to the terminal

How to run:
  python report_generator.py riti_risk_assessment.json

  (replace with your actual Phase 2 output filename)
=============================================================
"""

import anthropic
import json
import os
import sys
from datetime import date


# ─────────────────────────────────────────────────────────────
#  The report generation prompt
#
#  Tells Claude to act as a security architect writing a formal
#  integration design document for internal review and sign-off.
# ─────────────────────────────────────────────────────────────

REPORT_PROMPT = """
You are a senior third-party security architect writing a formal Security
Integration Design Document for internal review and sign-off.

You will be given:
- A vendor intake summary (name, use case, data types, access method)
- A full security interview transcript (questions and answers)
- A structured risk assessment across 5 security domains

Your job is to produce a complete Security Design Document in Markdown format
with the following sections:

---

# Security Integration Design Document
## [Vendor Name] — [Use Case]

### 1. Executive Summary
- One paragraph summarising the integration, its risk level, and the onboarding decision
- Clearly state: APPROVED FOR ONBOARDING, CONDITIONALLY APPROVED, or NOT APPROVED
- If conditionally approved or not approved, state what must change first

### 2. Vendor Overview
- Vendor name, use case, data types accessed, integration method
- Date of assessment

### 3. Risk Summary Table
A markdown table with columns: Domain | Risk Rating | Key Finding
Cover all 5 domains: Authentication, Data Exposure, Network Boundary, Blast Radius, Incident Response

### 4. Domain Findings
For each of the 5 domains, write a subsection with:
- Risk rating (LOW / MEDIUM / HIGH / CRITICAL)
- What was found (2-3 sentences from the interview answers)
- Specific risk flags identified
- Recommended remediation action

### 5. Pre-Onboarding Requirements
Two lists:

**Blockers (must be resolved before any data access is granted):**
- Numbered list of critical and high findings that block onboarding

**Recommendations (should be addressed within 90 days):**
- Numbered list of medium findings and best-practice improvements

### 6. Security Controls Checklist
A markdown checklist of controls the vendor must confirm are in place before go-live.
Include at least 8 specific, technical items derived from the assessment findings.

### 7. Reviewer Sign-Off
A table with columns: Role | Name | Date | Signature
Include rows for: Security Architect, Data Protection Officer, Engineering Lead, CISO

---

Rules:
- Write in formal, professional language suitable for an internal audit document
- Be specific — reference actual answers from the interview transcript
- Do not invent findings not supported by the transcript
- Output valid Markdown only — no preamble, no explanation outside the document
"""


# ─────────────────────────────────────────────────────────────
#  STEP 1: Load the Phase 2 JSON file
# ─────────────────────────────────────────────────────────────

def load_assessment(filepath):
    if not os.path.exists(filepath):
        print(f"\n❌ File not found: {filepath}")
        print("   Make sure you ran risk_classifier.py first.\n")
        sys.exit(1)

    with open(filepath, "r") as f:
        data = json.load(f)

    if "risk_assessment" not in data:
        print("\n❌ This file does not contain a risk assessment.")
        print("   Run risk_classifier.py first to generate Phase 2 output.\n")
        sys.exit(1)

    return data


# ─────────────────────────────────────────────────────────────
#  STEP 2: Build the prompt payload for Claude
# ─────────────────────────────────────────────────────────────

def build_prompt(assessment_data):
    intake    = assessment_data.get("vendor_intake", {})
    qa_pairs  = assessment_data.get("interview", [])
    risk      = assessment_data.get("risk_assessment", {})

    lines = []
    lines.append("=== VENDOR INTAKE ===")
    lines.append(f"Vendor:        {intake.get('vendor_name', 'Unknown')}")
    lines.append(f"Use case:      {intake.get('use_case', 'Unknown')}")
    lines.append(f"Data accessed: {intake.get('data_types', 'Unknown')}")
    lines.append(f"Access method: {intake.get('access_method', 'Unknown')}")
    lines.append(f"Assessment date: {date.today().isoformat()}")
    lines.append("")
    lines.append("=== INTERVIEW TRANSCRIPT ===")
    for qa in qa_pairs:
        lines.append(f"\nQ{qa['question_number']}: {qa['question']}")
        lines.append(f"A:  {qa['answer']}")

    lines.append("")
    lines.append("=== RISK ASSESSMENT ===")
    lines.append(json.dumps(risk, indent=2))

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  STEP 3: Generate the report with Claude
# ─────────────────────────────────────────────────────────────

def generate_report(client, prompt_text):
    print("\n[Generating Security Design Document with Claude...]\n")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=REPORT_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Please generate the Security Design Document for this assessment:\n\n{prompt_text}"
            }
        ]
    )

    return response.content[0].text


# ─────────────────────────────────────────────────────────────
#  STEP 4: Save the report as a Markdown file
# ─────────────────────────────────────────────────────────────

def save_report(vendor_name, report_markdown):
    vendor_slug = vendor_name.lower().replace(" ", "_").replace("/", "_")
    filename = f"{vendor_slug}_security_design_doc.md"

    with open(filename, "w") as f:
        f.write(report_markdown)

    return filename


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ ANTHROPIC_API_KEY not set.")
        print('   Run: export ANTHROPIC_API_KEY="sk-ant-..."\n')
        sys.exit(1)

    if len(sys.argv) < 2:
        print("\n❌ Please provide your risk assessment file as an argument.")
        print("   Example: python report_generator.py riti_risk_assessment.json\n")
        sys.exit(1)

    input_file = sys.argv[1]

    client          = anthropic.Anthropic(api_key=api_key)
    assessment_data = load_assessment(input_file)
    prompt_text     = build_prompt(assessment_data)
    report_markdown = generate_report(client, prompt_text)

    vendor_name = assessment_data.get("vendor_intake", {}).get("vendor_name", "vendor")
    output_file = save_report(vendor_name, report_markdown)

    print(report_markdown)
    print("\n" + "="*60)
    print(f"✅ Security Design Document saved to: {output_file}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
