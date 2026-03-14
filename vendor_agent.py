"""
=============================================================
  Vendor Secure Integration Design Agent  —  Phase 1
=============================================================

What this script does:
  1. Asks you for basic info about the vendor integration
  2. Sends that info to Claude with a security-expert system prompt
  3. Claude generates targeted security interview questions one at a time
  4. You answer each question in the terminal
  5. At the end, all answers are saved to a JSON file for Phase 2

How to run:
  1. Install the Anthropic library:      pip install anthropic
  2. Set your API key as an env variable: export ANTHROPIC_API_KEY="sk-ant-..."
  3. Run the script:                      python vendor_agent.py
=============================================================
"""

import anthropic  # The official Anthropic Python library
import json       # For saving answers to a file at the end
import os         # For reading the API key from your environment


# ─────────────────────────────────────────────────────────────
#  STEP 1: Define the "brain" of the agent — the system prompt
#
#  This is the most important part. The system prompt tells Claude
#  to act like a senior security architect at a company like Shopify.
#  All the security knowledge you have in your head lives here.
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


# ─────────────────────────────────────────────────────────────
#  STEP 2: Collect basic intake info from the person running
#          the script (you, the security analyst)
# ─────────────────────────────────────────────────────────────

def collect_intake():
    """
    Asks a few simple questions to set the context before the
    AI interview begins. Returns a dictionary with the answers.
    """
    print("\n" + "="*60)
    print("  VENDOR SECURE INTEGRATION DESIGN AGENT  —  Phase 1")
    print("="*60)
    print("\nLet's start with some basic context about this vendor.\n")

    # input() shows a prompt and waits for the user to type something + hit Enter
    vendor_name    = input("Vendor / company name: ").strip()
    use_case       = input("What is the integration use case? (e.g. 'analytics on hashed merchant PII'): ").strip()
    data_types     = input("What data types will they access? (e.g. 'hashed PII, transaction records'): ").strip()
    access_method  = input("How will they connect? (e.g. 'GCP service account', 'REST API', 'direct DB'): ").strip()

    # Bundle all intake answers into a Python dictionary (like a JSON object)
    intake = {
        "vendor_name":   vendor_name,
        "use_case":      use_case,
        "data_types":    data_types,
        "access_method": access_method,
    }

    return intake


# ─────────────────────────────────────────────────────────────
#  STEP 3: Build the opening message Claude will receive
#
#  Claude has no memory between conversations. We need to give
#  it the intake info in the very first message so it has context.
# ─────────────────────────────────────────────────────────────

def build_opening_message(intake):
    """
    Converts the intake dictionary into a natural-language message
    that Claude will receive as the first user turn.
    """
    return (
        f"We have a new vendor integration request. Here is the intake summary:\n\n"
        f"- Vendor: {intake['vendor_name']}\n"
        f"- Use case: {intake['use_case']}\n"
        f"- Data they need access to: {intake['data_types']}\n"
        f"- Integration method: {intake['access_method']}\n\n"
        f"Please begin the security interview. Ask your first question."
    )


# ─────────────────────────────────────────────────────────────
#  STEP 4: Run the interview loop
#
#  This is the core of the agent. It:
#    - Sends the conversation history to Claude
#    - Prints Claude's question
#    - Waits for your answer
#    - Appends both to the conversation history
#    - Repeats until we've asked enough questions
# ─────────────────────────────────────────────────────────────

def run_interview(client, intake, num_questions=7):
    """
    Runs a back-and-forth interview between Claude (the interviewer)
    and the user (who answers on the vendor's behalf, or relays answers).

    client        — the Anthropic API client object
    intake        — the basic info collected in Step 2
    num_questions — how many security questions to ask (default: 7)

    Returns a list of question/answer pairs.
    """

    # conversation_history is a list of message objects.
    # Each message has a "role" (either "user" or "assistant") and "content" (the text).
    # We always send the FULL history to Claude — it has no memory otherwise.
    conversation_history = [
        {
            "role": "user",
            "content": build_opening_message(intake)
        }
    ]

    # This list will store each question and answer for saving later
    qa_pairs = []

    print("\n" + "─"*60)
    print("  SECURITY INTERVIEW STARTING")
    print("  Answer each question as the vendor (or on their behalf).")
    print("  Type your answer and press Enter.")
    print("─"*60 + "\n")

    for question_number in range(1, num_questions + 1):

        print(f"[Asking question {question_number} of {num_questions}...]")

        # ── Call the Claude API ──────────────────────────────────
        # client.messages.create() sends our conversation to Claude
        # and returns its response.
        response = client.messages.create(
            model="claude-sonnet-4-6",          # The Claude model to use
            max_tokens=512,                      # Max length of Claude's reply
            system=SYSTEM_PROMPT,                # The security expert persona
            messages=conversation_history        # The full conversation so far
        )

        # Extract the text from Claude's response.
        # response.content is a list; [0].text gets the first text block.
        claude_question = response.content[0].text

        # Print Claude's question nicely
        print(f"\n🔒 Security Agent:\n{claude_question}\n")

        # Wait for the user's answer
        vendor_answer = input("Your answer: ").strip()

        # If the user typed nothing, record it as a placeholder
        if not vendor_answer:
            vendor_answer = "[No answer provided]"

        # Save this Q&A pair
        qa_pairs.append({
            "question_number": question_number,
            "question": claude_question,
            "answer":   vendor_answer,
        })

        # Add Claude's question to the history as an "assistant" message
        conversation_history.append({
            "role": "assistant",
            "content": claude_question
        })

        # Add the vendor's answer to the history as a "user" message
        conversation_history.append({
            "role": "user",
            "content": vendor_answer
        })

        print()  # Blank line for readability

    return qa_pairs


# ─────────────────────────────────────────────────────────────
#  STEP 5: Save everything to a JSON file
#
#  JSON is just a structured text format — like a Python dictionary
#  saved to disk. This file will be the input for Phase 2 (risk
#  classification) and Phase 3 (report generation).
# ─────────────────────────────────────────────────────────────

def save_results(intake, qa_pairs):
    """
    Saves the intake info and all Q&A pairs to a JSON file.
    The filename includes the vendor name so it's easy to find.
    """
    # Build a "slug" — a safe filename from the vendor name
    # e.g. "Acme Corp" → "acme_corp"
    vendor_slug = intake["vendor_name"].lower().replace(" ", "_").replace("/", "_")
    filename = f"{vendor_slug}_security_interview.json"

    # Bundle everything together
    output = {
        "vendor_intake": intake,
        "interview": qa_pairs,
        "status": "phase_1_complete — ready for risk classification"
    }

    # Write to file. "w" means write mode. indent=2 makes it human-readable.
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    return filename


# ─────────────────────────────────────────────────────────────
#  STEP 6: Main function — ties everything together
#
#  In Python, if __name__ == "__main__" means: only run this
#  block when you execute the file directly (not when it's
#  imported by another script).
# ─────────────────────────────────────────────────────────────

def main():

    # ── Check for API key ────────────────────────────────────
    # Your API key is stored as an environment variable, not
    # hardcoded in the script (never hardcode secrets in code!).
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable not set.")
        print("   Run this in your terminal first:")
        print('   export ANTHROPIC_API_KEY="sk-ant-your-key-here"\n')
        return

    # ── Create the Anthropic client ──────────────────────────
    # This is the object we use to make all API calls.
    client = anthropic.Anthropic(api_key=api_key)

    # ── Run the three phases ─────────────────────────────────
    intake   = collect_intake()
    qa_pairs = run_interview(client, intake, num_questions=7)
    filename = save_results(intake, qa_pairs)

    # ── Done ─────────────────────────────────────────────────
    print("─"*60)
    print(f"✅ Interview complete. {len(qa_pairs)} questions answered.")
    print(f"📄 Saved to: {filename}")
    print("\nNext step: Phase 2 — feed this JSON into the risk classifier.")
    print("─"*60 + "\n")


if __name__ == "__main__":
    main()
