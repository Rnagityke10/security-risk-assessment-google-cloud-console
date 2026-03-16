# Security Integration Design Document
## Google Analytics — Clean Room Hashed Merchant PII Matching

---

### 1. Executive Summary

Google Analytics has been assessed for integration into a clean room environment hosted within our GCP infrastructure, in which hashed merchant PII (name, email, and order data) will be matched against vendor-provided identifiers for analytics purposes. The integration leverages a GCP service account via Workload Identity Federation and is bounded by a VPC Service Controls perimeter. While several foundational technical controls are sound — notably the authentication mechanism and network boundary design — the assessment has identified two HIGH-rated domains and one MEDIUM-rated domain that present material, unresolved risk. Specifically, the clean room output dataset has been confirmed to contain enriched records combining hashed merchant PII with vendor-provided identifiers, the schema of which remains undefined and unreviewed, creating unquantified re-identification risk. This enriched data is subject to cross-border transfer from Montreal to Atlanta without a documented legal transfer mechanism under GDPR Chapter V or Quebec Law 25. Additionally, the vendor's 48-hour breach notification commitment is not contractually aligned with the data controller's obligations under GDPR Article 33. The SHA256 hashing scheme applied to input data lacks salting, introducing rainbow table vulnerability against predictable fields such as email addresses.

**Decision: CONDITIONALLY APPROVED**

The following must be resolved in full before any data access is granted: (1) formal written definition and security review of the clean room output schema; (2) documented legal basis and transfer mechanism for the Montreal-to-Atlanta data flow under GDPR and Quebec Law 25; (3) a contractually aligned breach notification SLA that preserves the controller's ability to meet the GDPR Article 33 72-hour supervisory authority notification window; and (4) upgrade of the hashing scheme from unsalted SHA256 to HMAC-SHA256 with a platform-controlled salt.

---

### 2. Vendor Overview

| Field | Detail |
|---|---|
| **Vendor Name** | Google Analytics |
| **Use Case** | Clean room environment for hashed merchant PII matching against vendor-provided identifiers for analytics purposes |
| **Data Types Accessed** | Hashed merchant PII: name, email, order data; enriched output records combining hashed PII with vendor-provided IDs |
| **Integration Method** | GCP service account via Workload Identity Federation; BigQuery Viewer IAM role |
| **Clean Room Location** | Montreal (GCP) |
| **Output Data Destination** | Vendor GCP environment, Atlanta |
| **Assessment Date** | 2026-03-15 |

---

### 3. Risk Summary Table

| Domain | Risk Rating | Key Finding |
|---|---|---|
| Authentication | LOW | Workload Identity Federation confirmed; no long-lived exportable JSON key files in use |
| Data Exposure | HIGH | SHA256 applied without salting; output dataset confirmed to contain enriched records combining hashed PII with vendor IDs; schema undefined and unreviewed |
| Network Boundary | LOW | Access confined within a VPC Service Controls perimeter, materially limiting API-level exfiltration and lateral movement risk |
| Blast Radius | MEDIUM | BigQuery Viewer role requested, but binding scope not confirmed as dataset-level; enriched output export path extends risk surface beyond the clean room boundary |
| Incident Response | HIGH | Vendor's 48-hour breach notification commitment not contractually aligned with GDPR Article 33 72-hour window; Montreal-to-Atlanta cross-border transfer lacks documented legal mechanism; no confirmation that monitoring covers GCP audit logs and BigQuery access patterns |

---

### 4. Domain Findings

---

#### 4.1 Authentication

**Risk Rating: LOW**

**Findings:**
The vendor confirmed that authentication to the GCP service account will be performed exclusively via Workload Identity Federation (WIF), with no exported JSON key files in use. This eliminates the primary risk associated with long-lived, portable credentials that may be exfiltrated, rotated improperly, or stored insecurely outside the GCP environment. No flags were raised against this domain during the interview.

**Risk Flags Identified:**
- None identified. Residual risk is low provided the vendor-side identity provider is appropriately hardened and token lifetimes are minimised.

**Recommended Remediation:**
Request formal documentation of the vendor's identity provider (IdP) configuration, including token lifetime settings and any conditions applied to the WIF binding. Confirm that the WIF binding is scoped to a specific vendor GCP project identifier rather than a broad or unrestricted identity pool, and retain this documentation on file prior to go-live.

---

#### 4.2 Data Exposure

**Risk Rating: HIGH**

**Findings:**
The vendor confirmed that SHA256 is the hashing algorithm applied to merchant PII inputs, with no plaintext reconstitution occurring on the vendor side. However, SHA256 is applied without salting, which exposes predictable-format fields — most critically email addresses — to rainbow table attacks using pre-computed hash dictionaries. More significantly, the vendor confirmed during the blast radius discussion that the clean room output dataset contains enriched records combining our hashed PII with vendor-provided identifiers, but was unable to define the schema of that matched dataset when directly asked. No formal schema review or approval process exists for clean room output prior to export authorisation.

**Risk Flags Identified:**
- SHA256 hashing applied to input fields without a platform-controlled salt, creating rainbow table vulnerability on predictable fields such as email addresses
- Vendor confirmed enriched records are present in the output dataset but could not define the matched dataset schema when asked directly
- Combined hashed PII and vendor-provided IDs in a single output record materially elevates re-identification risk above either input dataset in isolation
- No formal output schema definition, review, or approval process exists prior to clean room export authorisation

**Recommended Remediation:**
Require the vendor to adopt HMAC-SHA256 with a platform-controlled salt — owned and rotated by our organisation — applied to all PII fields before data enters the clean room. Mandate formal written schema documentation covering all fields, data types, and join keys present in the clean room output dataset. This schema must undergo a dedicated security and data protection review and receive written approval before any export from the clean room is authorised under any circumstance.

---

#### 4.3 Network Boundary

**Risk Rating: LOW**

**Findings:**
The vendor confirmed that all access to resources within our GCP environment will occur within a VPC Service Controls perimeter. This architecture significantly limits the risk of data exfiltration through GCP API abuse, prevents lateral movement to resources outside the defined boundary, and reduces the exposure surface compared to public-internet-accessible integration patterns. No flags were raised against this domain during the interview.

**Risk Flags Identified:**
- None identified. Residual risk is low, contingent on the VPC-SC perimeter policy being correctly configured and actively maintained.

**Recommended Remediation:**
Conduct a joint technical review of the VPC Service Controls perimeter policy prior to go-live to confirm that no unintended egress paths, access levels, or service exceptions exist. Ensure that perimeter violation alerts are actively monitored in near real time by our internal security operations function, and that alert coverage is explicitly documented.

---

#### 4.4 Blast Radius

**Risk Rating: MEDIUM**

**Findings:**
The vendor stated that the requested IAM role is BigQuery Viewer only, which represents a reasonable least-privilege posture for a read-oriented clean room integration. However, the vendor did not confirm whether the role binding is scoped at the dataset level or at the broader project or organisation level; the distinction is material, as a project-level binding would grant read access to all BigQuery datasets within the project rather than exclusively the clean room dataset. Additionally, the vendor confirmed that enriched output records are exported to the vendor's own GCP environment in Atlanta, extending the effective data access boundary beyond our controlled clean room perimeter. Export trigger controls were described as being restricted to approved personnel, but no technical enforcement mechanism — such as an IAM condition, approval workflow, or audit-log-based gate — was described.

**Risk Flags Identified:**
- IAM role binding scope not confirmed as dataset-level; a project-level or organisation-level binding would materially expand the blast radius beyond the clean room dataset
- Enriched output records are exported to the vendor's GCP environment, extending the risk surface and data custody outside our direct control
- Export trigger controls are described in personnel terms only, with no confirmed technical enforcement mechanism preventing unauthorised export

**Recommended Remediation:**
Verify and enforce — via GCP IAM policy inspection — that the BigQuery Viewer role binding is applied at the dataset resource level scoped exclusively to the clean room dataset, not at the GCP project or organisation level. Implement audit-log-based alerting on all BigQuery export trigger events originating from or associated with the vendor service account. Document and technically enforce the approved personnel designation through IAM conditions or an equivalent access control mechanism.

---

#### 4.5 Incident Response

**Risk Rating: HIGH**

**Findings:**
The vendor confirmed that internal alerting is in place covering their DART and infosec teams, which represents a positive baseline control. However, the vendor did not confirm that this alerting specifically covers GCP audit log events and BigQuery data access patterns within our environment, as opposed to vendor-side infrastructure monitoring only. The vendor committed to a 48-hour breach notification timeline on their side. This creates a material compliance gap: as the data controller, our organisation's GDPR Article 33 obligation to notify the relevant supervisory authority within 72 hours begins at the point we become aware of a breach — which, in practice, should commence when the vendor detects it. A 48-hour vendor notification window leaves insufficient headroom for internal triage, legal assessment, and regulatory notification within the 72-hour window. Furthermore, the data flow from Montreal to Atlanta has not been assessed against GDPR Chapter V transfer mechanisms or Quebec Law 25, and no Data Processing Agreement or contractual breach notification SLA was referenced during the interview.

**Risk Flags Identified:**
- Vendor's 48-hour breach notification commitment is not contractually aligned with the data controller's GDPR Article 33 72-hour supervisory authority notification obligation
- No confirmation that vendor-side alerting covers GCP audit logs and BigQuery data access patterns within our environment specifically
- Montreal-to-Atlanta data flow introduces cross-border transfer risk under GDPR Chapter V and Quebec Law 25 with no documented legal transfer mechanism provided
- No Data Processing Agreement or contractual breach notification SLA was referenced during the assessment

**Recommended Remediation:**
Contractually mandate a vendor breach notification timeline that preserves sufficient margin for the data controller to meet the GDPR Article 33 72-hour supervisory authority notification requirement — a vendor notification obligation of no more than 24 hours from detection is recommended. Require written confirmation that vendor monitoring explicitly covers GCP audit log events and BigQuery data access patterns within our clean room environment. Engage legal counsel immediately to establish and document a valid GDPR Chapter V transfer mechanism and Quebec Law 25 compliance basis for the Montreal-to-Atlanta data flow before any data transfer is permitted. A fully executed Data Processing Agreement must be in place prior to go-live.

---

### 5. Pre-Onboarding Requirements

**Blockers (must be resolved before any data access is granted):**

1. The clean room output dataset schema must be formally and completely documented in writing, identifying all fields, data types, join keys, and the nature of enrichment applied; this schema must undergo a dedicated security and data protection review and receive written sign-off before any export from the clean room is authorised.
2. The hashing scheme applied to all merchant PII input fields must be upgraded from unsalted SHA256 to HMAC-SHA256 using a platform-controlled salt owned and managed by our organisation; technical implementation must be validated by our GCP security team prior to any data being loaded into the clean room.
3. A valid legal transfer mechanism under GDPR Chapter V (e.g., Standard Contractual Clauses) and a compliance basis under Quebec Law 25 must be documented and approved by legal counsel before any data transfer from Montreal to Atlanta is permitted.
4. A fully executed Data Processing Agreement (DPA) must be in place that contractually binds the vendor to a breach notification timeline of no more than 24 hours from detection, preserving the data controller's ability to meet the GDPR Article 33 72-hour supervisory authority notification window.
5. The BigQuery Viewer IAM role binding must be verified by GCP IAM policy inspection to be scoped exclusively at the clean room dataset resource level, and not at the GCP project or organisation level; written evidence of this verification must be provided.

**Recommendations (should be addressed within 90 days):**

1. Conduct a joint technical review of the VPC Service Controls perimeter policy to confirm that no unintended egress paths, service exceptions, or overly permissive access levels exist within the perimeter configuration.
2. Obtain and retain on file formal documentation of the vendor's Workload Identity Federation configuration, including identity provider details, token lifetime settings, and the specific GCP project scope of the WIF binding.
3. Implement audit-log-based alerting covering all BigQuery export trigger events associated with the vendor service account, and confirm that this alerting is integrated into our security operations monitoring function with defined response procedures.
4. Require written confirmation from the vendor that their DART and infosec team alerting explicitly covers GCP audit log events and BigQuery data access patterns within our environment, not solely vendor-side infrastructure.
5. Establish a technical enforcement mechanism — such as an IAM condition or formal access approval workflow — that enforces the approved personnel designation for clean room export triggers, replacing the current personnel-only control.

---

### 6. Security Controls Checklist

The following controls must be confirmed as in place by the vendor and verified by our GCP security team before go-live is authorised. All items are mandatory.

- [ ] **HMAC-SHA256 with platform-controlled salt** is applied to all merchant PII fields (name, email, order data) prior to ingestion into the clean room; unsalted SHA256 is not used at any stage of the pipeline
- [ ] **Workload Identity Federation** is the sole authentication mechanism for the vendor service account; no JSON key files have been exported, stored, or distributed at any point
- [ ] **WIF binding is scoped to a specific, named vendor GCP project identifier** and does not reference a broad or unrestricted identity pool; documentation confirming this configuration is on file
- [ ] **BigQuery Viewer IAM role binding is confirmed at dataset resource level** scoped exclusively to the clean room dataset; GCP IAM policy output has been inspected and signed off by our GCP security team; no project-level or organisation-level bindings exist for this service account
- [ ] **Clean room output schema is formally documented and approved**, including all fields, data types, join keys, and enrichment operations; this document has received written sign-off from the Security Architect and Data Protection Officer prior to any export being enabled
- [ ] **VPC Service Controls perimeter policy has been jointly reviewed**, with no unintended egress paths, access level exceptions, or service-specific bypass rules present; perimeter violation alerts are actively monitored in near real time
- [ ] **A fully executed Data Processing Agreement is in place** that specifies a vendor breach notification obligation of no more than 24 hours from detection, explicitly aligned to support the controller's GDPR Article 33 72-hour supervisory authority notification window
- [ ] **A documented GDPR Chapter V transfer mechanism** (e.g., Standard Contractual Clauses) and a Quebec Law 25 compliance basis have been approved by legal counsel and are on file prior to any data transfer from Montreal to Atlanta
- [ ] **Vendor monitoring and alerting explicitly covers GCP audit log events and BigQuery data access patterns** within our clean room environment; written confirmation from the vendor's infosec team specifying this coverage has been received and retained on file
- [ ] **Audit-log-based alerting on BigQuery export trigger events** associated with the vendor service account is active, tested, and integrated into our internal security operations monitoring function with a defined incident response runbook

---

### 7. Reviewer Sign-Off

| Role | Name | Date | Signature |
|---|---|---|---|
| Security Architect | | | |
| Data Protection Officer | | | |
| Engineering Lead | | | |
| CISO | | | |

---

*This document is confidential and intended for internal review and sign-off only. It must not be shared with the vendor or any external party without prior written authorisation from the CISO. Document version: 1.0. Assessment date: 2026-03-15.*