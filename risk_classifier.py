"""
=============================================================
  Vendor Secure Integration Design Agent  —  Phase 2
  Risk Classifier
=============================================================

What this script does:
  1. Reads the JSON file produced by Phase 1 (vendor_agent.py)
  2. Sends the full interview transcript to Claude
  3. Claude scores risk across 5 security domains
  4. Results are printed to the terminal as a risk report
  5. The scored output is saved to a new JSON file for Phase 3

How to run:
  python risk_classifier.py riti_security_interview.json

  (replace riti_security_interview.json with your actual filename)
=============================================================
"""

import anthropic
import json
import os
import sys                  # sys lets us read arguments typed after the script name


# ─────────────────────────────────────────────────────────────
#  The risk classification prompt
#
#  This tells Claude to act as a risk analyst and score the
#  interview transcript across five security domains.
#  The key instruction is: respond ONLY in JSON, no extra text.
#  That lets us reliably parse the output in Python.
# ─────────────────────────────────────────────────────────────

CLASSIFIER_PROMPT = """
You are a senior third-party security risk analyst. You will be given a
security interview transcript with a vendor who wants to integrate into
a sensitive cloud environment (GCP) that hosts hashed PII data.

Your job is to read every question and answer in the transcript, then
produce a structured risk assessment across these five domains:

1. authentication       — How the vendor proves its identity (service account keys,
                          Workload Identity Federation, OAuth, etc.)
2. data_exposure        — What PII or sensitive data the vendor can access, and how
3. network_boundary     — Where traffic travels and through what controls
4. blast_radius         — Worst-case scope if this vendor's access is compromised
5. incident_response    — Vendor's ability to detect, contain, and report a breach

For each domain, assign:
- "rating": one of "low", "medium", "high", or "critical"
- "summary": one sentence describing the finding
- "flags": a list of specific risk indicators found in the answers (empty list if none)
- "recommendation": one concrete action to reduce the risk

Also produce an overall assessment:
- "overall_risk": one of "low", "medium", "high", or "critical"
- "top_concern": the single most important risk in one sentence
- "cleared_for_onboarding": true or false

Rating guide:
  low      — standard controls in place, no immediate concerns
  medium   — gaps exist but are manageable with documented mitigations
  high     — significant gaps that must be resolved before onboarding
  critical — fundamental security failure; do not onboard without major remediation

IMPORTANT: Respond with ONLY a valid JSON object. No preamble, no explanation,
no markdown code fences. Just the raw JSON, starting with { and ending with }.
"""


# ─────────────────────────────────────────────────────────────
#  STEP 1: Load the Phase 1 JSON file
# ─────────────────────────────────────────────────────────────

def load_interview(filepath):
    """
    Reads the JSON file from Phase 1 and returns it as a Python dictionary.
    Exits with a clear error message if the file isn't found.
    """
    if not os.path.exists(filepath):
        print(f"\n❌ File not found: {filepath}")
        print("   Make sure you ran vendor_agent.py first and the file is in this folder.\n")
        sys.exit(1)

    with open(filepath, "r") as f:
        data = json.load(f)

    return data


# ─────────────────────────────────────────────────────────────
#  STEP 2: Format the interview into a readable transcript
#
#  We turn the list of Q&A pairs into a plain-text transcript
#  that's easy for Claude to read and reason about.
# ─────────────────────────────────────────────────────────────

def format_transcript(interview_data):
    """
    Converts the structured JSON from Phase 1 into a plain-text
    transcript Claude can analyse.
    """
    intake = interview_data.get("vendor_intake", {})
    qa_pairs = interview_data.get("interview", [])

    # Build the transcript string piece by piece
    lines = []
    lines.append("=== VENDOR INTAKE ===")
    lines.append(f"Vendor:        {intake.get('vendor_name', 'Unknown')}")
    lines.append(f"Use case:      {intake.get('use_case', 'Unknown')}")
    lines.append(f"Data accessed: {intake.get('data_types', 'Unknown')}")
    lines.append(f"Access method: {intake.get('access_method', 'Unknown')}")
    lines.append("")
    lines.append("=== SECURITY INTERVIEW TRANSCRIPT ===")

    for qa in qa_pairs:
        lines.append(f"\nQ{qa['question_number']}: {qa['question']}")
        lines.append(f"A:  {qa['answer']}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  STEP 3: Send the transcript to Claude for risk scoring
# ─────────────────────────────────────────────────────────────

def classify_risk(client, transcript):
    """
    Sends the interview transcript to Claude and asks it to return
    a structured JSON risk assessment.
    """
    print("\n[Analysing transcript with Claude...]\n")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=CLASSIFIER_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Please assess the risk in this vendor interview:\n\n{transcript}"
            }
        ]
    )

    raw_text = response.content[0].text

    # Parse the JSON Claude returned
    # If Claude added any stray text, strip it before parsing
    try:
        risk_data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Sometimes Claude wraps output in ```json ... ``` even when told not to
        # This strips those fences if present
        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        risk_data = json.loads(cleaned)

    return risk_data


# ─────────────────────────────────────────────────────────────
#  STEP 4: Print the risk report to the terminal
#
#  This is what you actually read — a clear, colour-coded
#  summary of every risk domain.
# ─────────────────────────────────────────────────────────────

# Maps risk ratings to visual indicators for the terminal
RISK_ICONS = {
    "low":      "🟢 LOW",
    "medium":   "🟡 MEDIUM",
    "high":     "🔴 HIGH",
    "critical": "🚨 CRITICAL",
}

def print_report(vendor_name, risk_data):
    """
    Prints a formatted risk report to the terminal.
    """
    overall = risk_data.get("overall_risk", "unknown").lower()
    cleared = risk_data.get("cleared_for_onboarding", False)
    top_concern = risk_data.get("top_concern", "")

    print("=" * 60)
    print(f"  VENDOR RISK ASSESSMENT: {vendor_name.upper()}")
    print("=" * 60)

    print(f"\n  Overall risk:     {RISK_ICONS.get(overall, overall.upper())}")
    cleared_label = "✅ YES — cleared for onboarding" if cleared else "❌ NO — do not onboard yet"
    print(f"  Cleared:          {cleared_label}")
    print(f"  Top concern:      {top_concern}")

    print("\n" + "─" * 60)
    print("  DOMAIN BREAKDOWN")
    print("─" * 60)

    # Print each domain's finding
    domain_labels = {
        "authentication":    "Authentication",
        "data_exposure":     "Data exposure",
        "network_boundary":  "Network boundary",
        "blast_radius":      "Blast radius",
        "incident_response": "Incident response",
    }

    for key, label in domain_labels.items():
        # Domains are stored directly in risk_data, not nested under a "domains" key
        domain = risk_data.get(key, {})
        rating = domain.get("rating", "unknown").lower()
        summary = domain.get("summary", "")
        flags = domain.get("flags", [])
        recommendation = domain.get("recommendation", "")

        print(f"\n  {label}")
        print(f"  Risk:   {RISK_ICONS.get(rating, rating.upper())}")
        print(f"  Found:  {summary}")

        if flags:
            for flag in flags:
                print(f"          ⚠️  {flag}")

        print(f"  Fix:    {recommendation}")

    print("\n" + "=" * 60)
    print("  Next step: Phase 3 — generate full security design doc")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────
#  STEP 5: Save the risk assessment to a new JSON file
# ─────────────────────────────────────────────────────────────

def save_risk_output(interview_data, risk_data):
    """
    Saves a combined file containing the original interview
    plus the risk assessment. Phase 3 will read this file.
    """
    vendor_name = interview_data.get("vendor_intake", {}).get("vendor_name", "vendor")
    vendor_slug = vendor_name.lower().replace(" ", "_").replace("/", "_")
    filename = f"{vendor_slug}_risk_assessment.json"

    output = {
        "vendor_intake":    interview_data.get("vendor_intake", {}),
        "interview":        interview_data.get("interview", []),
        "risk_assessment":  risk_data,
        "status": "phase_2_complete — ready for report generation"
    }

    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    return filename


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────

def main():

    # ── Check API key ────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ ANTHROPIC_API_KEY not set.")
        print('   Run: export ANTHROPIC_API_KEY="sk-ant-..."\n')
        sys.exit(1)

    # ── Get the filename from the command line ───────────────
    # sys.argv is the list of words you typed in the terminal.
    # sys.argv[0] = "risk_classifier.py"
    # sys.argv[1] = the filename you passed after the script name
    if len(sys.argv) < 2:
        print("\n❌ Please provide your interview file as an argument.")
        print("   Example: python risk_classifier.py riti_security_interview.json\n")
        sys.exit(1)

    input_file = sys.argv[1]

    # ── Run the pipeline ─────────────────────────────────────
    client         = anthropic.Anthropic(api_key=api_key)
    interview_data = load_interview(input_file)
    transcript     = format_transcript(interview_data)
    risk_data      = classify_risk(client, transcript)

    vendor_name    = interview_data.get("vendor_intake", {}).get("vendor_name", "Vendor")
    print_report(vendor_name, risk_data)

    output_file    = save_risk_output(interview_data, risk_data)

    print(f"📄 Full assessment saved to: {output_file}\n")


if __name__ == "__main__":
    main()
