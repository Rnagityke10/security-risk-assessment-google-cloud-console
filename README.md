# Vendor Secure Integration Design Agent

An AI-powered security interview tool that helps assess third-party vendor
integrations — covering authentication, data access, network boundaries,
egress controls, and incident response readiness.

Built using Python + the Claude API.

---

## What it does

- Takes basic vendor intake information (name, use case, data types, access method)
- Runs a structured 7-question security interview, powered by Claude
- Saves all questions and answers to a JSON file for downstream processing

---

## Setup (one time)

### 1. Install Python
Download from https://python.org — version 3.9 or higher.

### 2. Install the Anthropic library
Open your terminal and run:
```
pip install anthropic
```

### 3. Get your Claude API key
Go to https://console.anthropic.com → API Keys → Create Key

### 4. Set your API key in the terminal
On Mac/Linux:
```
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```
On Windows (Command Prompt):
```
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## Run it

```
python vendor_agent.py
```

---

## Project phases

| Phase | What it does | Status |
|-------|-------------|--------|
| 1 — Interview loop | Collects vendor intake + runs AI security interview | ✅ This file |
| 2 — Risk classifier | Reads the JSON + scores risk per security domain | 🔜 Next |
| 3 — Report generator | Produces a Markdown security design document | 🔜 Coming |
| 4 — Web UI | Wraps everything in a browser form (FastAPI) | 🔜 Coming |
| 5 — Database | Stores vendor assessments in SQLite | 🔜 Coming |

---

## Example output file

After running, you'll get a file like `acme_analytics_security_interview.json`:

```json
{
  "vendor_intake": {
    "vendor_name": "Acme Analytics",
    "use_case": "Analytics on hashed merchant PII",
    "data_types": "Hashed PII, transaction records",
    "access_method": "GCP service account"
  },
  "interview": [
    {
      "question_number": 1,
      "question": "Will your service authenticate using a long-lived service account key file, or are you able to support Workload Identity Federation for keyless authentication?",
      "answer": "We currently use key files but can support WIF."
    },
    ...
  ],
  "status": "phase_1_complete — ready for risk classification"
}
```
