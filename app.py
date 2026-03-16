"""
Vendor Security Assessment — Streamlit Web App
Wraps vendor_agent.py (Phase 1) and risk_classifier.py (Phase 2)
into a browser-based interface.
"""

import streamlit as st
import anthropic
import os
import json

from risk_classifier import format_transcript, classify_risk, RISK_ICONS

# ─────────────────────────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vendor Security Assessment",
    page_icon="🔒",
    layout="centered"
)

# ─────────────────────────────────────────────────────────────
#  Anthropic client (reads from environment)
# ─────────────────────────────────────────────────────────────

@st.cache_resource
def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)

# ─────────────────────────────────────────────────────────────
#  System prompt (same as vendor_agent.py)
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior third-party security architect at a large e-commerce platform.
Your job is to interview vendors who want to integrate with the platform's
internal environment — including GCP-hosted systems that may contain sensitive
or hashed PII data.

Your goal is to ask one focused security question at a time, based on:
- What the vendor has told you so far
- What has NOT yet been asked
- What a reasonable adversary would exploit if left unaddressed

You ask questions across these security domains, in rough order of priority:
1. Data classification    — What data is touched and how sensitive is it?
2. Authentication         — How does the vendor's system prove its identity?
3. Network boundary       — Where does traffic travel and through what controls?
4. Data egress            — Where does data go after the vendor processes it?
5. Blast radius           — What is the worst-case scope of a compromise?
6. Compliance / residency — Are there legal constraints on where data lives?
7. Incident response      — Is the vendor equipped to handle a breach?

Rules you follow:
- Ask exactly ONE question per response. Never ask two questions at once.
- Be specific and technical — do not ask vague questions like "is your system secure?"
- After the vendor answers, acknowledge the key security implication in one sentence,
  then ask the next most important question.
- If an answer reveals a high-risk pattern (e.g. long-lived service account keys,
  no egress controls, public internet access to PII), note it clearly with: ⚠️ RISK:
- Format: one short acknowledgement line, then the next question on a new line.
- Do not generate a report yet — just conduct the interview.
"""

NUM_QUESTIONS = 7

# ─────────────────────────────────────────────────────────────
#  Session state initialisation
# ─────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "step": "intake",           # intake | interview | results
        "intake": {},
        "conversation_history": [],
        "qa_pairs": [],
        "current_question": None,
        "risk_data": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# ─────────────────────────────────────────────────────────────
#  Helper: ask Claude for the next question
# ─────────────────────────────────────────────────────────────

def ask_claude(client):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=st.session_state.conversation_history
    )
    return response.content[0].text

# ─────────────────────────────────────────────────────────────
#  Step 1: Intake form
# ─────────────────────────────────────────────────────────────

def render_intake():
    st.title("🔒 Vendor Security Assessment")
    st.markdown("Fill in the details below to begin the security interview.")

    with st.form("intake_form"):
        vendor_name   = st.text_input("Vendor / company name")
        use_case      = st.text_input("Integration use case", placeholder="e.g. analytics on hashed merchant PII")
        data_types    = st.text_input("Data types they will access", placeholder="e.g. hashed PII, transaction records")
        access_method = st.text_input("How will they connect?", placeholder="e.g. GCP service account, REST API")
        submitted     = st.form_submit_button("Start Security Interview →")

    if submitted:
        if not all([vendor_name, use_case, data_types, access_method]):
            st.warning("Please fill in all fields before continuing.")
            return

        st.session_state.intake = {
            "vendor_name":   vendor_name,
            "use_case":      use_case,
            "data_types":    data_types,
            "access_method": access_method,
        }

        # Build the opening message for Claude
        opening = (
            f"We have a new vendor integration request. Here is the intake summary:\n\n"
            f"- Vendor: {vendor_name}\n"
            f"- Use case: {use_case}\n"
            f"- Data they need access to: {data_types}\n"
            f"- Integration method: {access_method}\n\n"
            f"Please begin the security interview. Ask your first question."
        )
        st.session_state.conversation_history = [{"role": "user", "content": opening}]
        st.session_state.qa_pairs = []

        # Get the first question from Claude
        client = get_client()
        with st.spinner("Starting interview..."):
            st.session_state.current_question = ask_claude(client)

        st.session_state.step = "interview"
        st.rerun()

# ─────────────────────────────────────────────────────────────
#  Step 2: Interview
# ─────────────────────────────────────────────────────────────

def render_interview():
    intake = st.session_state.intake
    qa_pairs = st.session_state.qa_pairs
    question_number = len(qa_pairs) + 1

    st.title("🔒 Security Interview")
    st.markdown(f"**Vendor:** {intake['vendor_name']} &nbsp;|&nbsp; **Question {question_number} of {NUM_QUESTIONS}**")
    st.progress(question_number / NUM_QUESTIONS)

    # Show previous Q&A
    if qa_pairs:
        with st.expander("Previous questions", expanded=False):
            for qa in qa_pairs:
                st.markdown(f"**Q{qa['question_number']}:** {qa['question']}")
                st.markdown(f"**Your answer:** {qa['answer']}")
                st.divider()

    # Current question
    st.markdown("### Security Agent asks:")
    st.info(st.session_state.current_question)

    with st.form("answer_form"):
        answer = st.text_area("Your answer", height=100, placeholder="Type your answer here...", key=f"answer_{question_number}")
        submitted = st.form_submit_button("Submit answer →")

    if submitted:
        if not answer.strip():
            st.warning("Please provide an answer before continuing.")
            return

        answer = answer.strip()

        # Save Q&A pair
        st.session_state.qa_pairs.append({
            "question_number": question_number,
            "question": st.session_state.current_question,
            "answer": answer,
        })

        # Add to conversation history
        st.session_state.conversation_history.append({"role": "assistant", "content": st.session_state.current_question})
        st.session_state.conversation_history.append({"role": "user", "content": answer})

        if question_number >= NUM_QUESTIONS:
            # Interview complete — run risk classification
            client = get_client()
            interview_data = {
                "vendor_intake": st.session_state.intake,
                "interview": st.session_state.qa_pairs,
            }
            with st.spinner("Analysing responses and calculating risk..."):
                transcript = format_transcript(interview_data)
                st.session_state.risk_data = classify_risk(client, transcript)
            st.session_state.step = "results"
        else:
            # Get next question
            client = get_client()
            with st.spinner("Getting next question..."):
                st.session_state.current_question = ask_claude(client)

        st.rerun()

# ─────────────────────────────────────────────────────────────
#  Step 3: Results
# ─────────────────────────────────────────────────────────────

RISK_COLORS = {
    "low":      "🟢",
    "medium":   "🟡",
    "high":     "🔴",
    "critical": "🚨",
}

DOMAIN_LABELS = {
    "authentication":    "Authentication",
    "data_exposure":     "Data Exposure",
    "network_boundary":  "Network Boundary",
    "blast_radius":      "Blast Radius",
    "incident_response": "Incident Response",
}

def render_results():
    risk = st.session_state.risk_data
    intake = st.session_state.intake
    vendor_name = intake["vendor_name"]

    overall = risk.get("overall_risk", "unknown").lower()
    cleared = risk.get("cleared_for_onboarding", False)
    top_concern = risk.get("top_concern", "")

    st.title(f"🔒 Risk Assessment: {vendor_name}")

    # Overall summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Overall Risk", f"{RISK_COLORS.get(overall, '')} {overall.upper()}")
    with col2:
        st.metric("Cleared for Onboarding", "✅ Yes" if cleared else "❌ No")

    st.markdown(f"**Top concern:** {top_concern}")
    st.divider()

    # Domain breakdown
    st.markdown("### Domain Breakdown")

    for key, label in DOMAIN_LABELS.items():
        domain = risk.get(key, {})
        rating = domain.get("rating", "unknown").lower()
        summary = domain.get("summary", "")
        flags = domain.get("flags", [])
        recommendation = domain.get("recommendation", "")
        icon = RISK_COLORS.get(rating, "")

        with st.expander(f"{icon} {label} — {rating.upper()}", expanded=(rating in ["high", "critical"])):
            st.markdown(f"**Finding:** {summary}")
            if flags:
                st.markdown("**Risk flags:**")
                for flag in flags:
                    st.markdown(f"- ⚠️ {flag}")
            st.markdown(f"**Recommendation:** {recommendation}")

    st.divider()

    # Download results
    full_output = {
        "vendor_intake": st.session_state.intake,
        "interview": st.session_state.qa_pairs,
        "risk_assessment": risk,
    }
    st.download_button(
        label="⬇️ Download full assessment (JSON)",
        data=json.dumps(full_output, indent=2),
        file_name=f"{vendor_name.lower().replace(' ', '_')}_risk_assessment.json",
        mime="application/json"
    )

    if st.button("Start a new assessment"):
        for key in ["step", "intake", "conversation_history", "qa_pairs", "current_question", "risk_data"]:
            del st.session_state[key]
        st.rerun()

# ─────────────────────────────────────────────────────────────
#  Router
# ─────────────────────────────────────────────────────────────

step = st.session_state.step

if step == "intake":
    render_intake()
elif step == "interview":
    render_interview()
elif step == "results":
    render_results()
