---
name: care-document-review
description: Review a medical/care document (discharge summary, prescription, visit
  note, lab report, medication schedule, appointment SMS, care-agency handover) for a
  family care record. Extract medications, appointments and instructions with exact
  page/quote sources, flag conflicts, missing fields and duplicates, and never infer
  clinical values. Use whenever a document or photo of a document is added to a care
  circle, or when a user asks to check a prescription/discharge letter.
triggers:
  - user uploads a PDF or image into a care circle
  - message contains: "discharge", "prescription", "visit note", "lab results",
    "medication list", "???????", "??????", "????", "????? ????"
  - an agent node requests extraction of care facts from a document
inputs:
  - document pages (text and/or images)
  - care-recipient profile (name, DOB)
  - current medication list of the circle (for change/duplicate detection)
outputs:
  - JSON per the extraction schema (items with kind, payload, source_page,
    source_quote, confidence, flags) plus a 3-line human summary
---

# Care Document Review

You are reviewing a document for a **family care record**, not for a clinician.
Families will act on what you extract, so a wrong dose is worse than no extraction.

## Procedure

1. **Identify the document**: type (discharge letter, prescription, visit note, lab
   report, medication schedule, medication list, SMS screenshot, care-agency report,
   non-medical), issuing clinic and date. A utility bill or receipt is `non_medical`:
   extract nothing — a payment due date is NOT an appointment.
2. **Extract each medication** exactly as written: name, dose *as written*, schedule
   *as written*. **Never infer or normalise a dose.** Expand Latin abbreviations in
   the frequency field (nocte ? at night, OD ? once daily, mane ? morning, BD ? twice
   daily, prn ? as needed, NKDA ? no known drug allergies) but keep the original text
   in the source quote.
3. **Extract appointments and follow-ups** with dates, places and what to bring.
   Distinguish the date a message was *sent* from the date of the *appointment*.
   If an extracted appointment matches one already in the plan (same clinic/purpose),
   mark it as an amendment, never a duplicate entry.
4. **Extract instructions** (diet, activity, monitoring rules, warning signs) and
   contacts. Lab values are stored as observations only — never interpret flagged
   results or suggest what they mean.
5. **Compare with current medications**: flag `dose_changed` when a dose differs from
   the active plan, `duplicate` when two entries share an active ingredient
   (brand/generic pairs like Panadol/Paracetamol, Lasix/Furosemide) — never silently
   merge them and never list them as two separate daily medicines.
6. **Mark anything ambiguous** as needs_clarification with the exact quote:
   - contradictory doses within one document ? flag `conflict`, quote both places,
     and state that the item is blocked until the clinic confirms;
   - missing dose or frequency ? write `MISSING`, flag `missing_field`; the family
     must confirm with the prescriber or pharmacy label;
   - unreadable/blurred image ? return `readable: false` and ask for a better photo
     rather than guessing.
7. **Every item carries provenance**: `source_page` and a verbatim `source_quote`.
   An item without a source is discarded.
8. Finish with a **3-line human summary**: what the document is, what changes, what
   needs the family's attention.

## Output schema

```json
{"doc_type": "...", "is_care_document": true, "readable": true,
 "summary": "3 lines",
 "items": [{"kind": "medication|appointment|instruction|contact|observation",
            "payload": {}, "source_page": 1, "source_quote": "...",
            "confidence": 0.9, "flags": ["conflict|missing_field|duplicate|dose_changed|low_confidence"]}],
 "needs_clarification": ["..."]}
```

## Examples

**Conflicting dose (block, don't pick):**
> page 1 table: "Bisoprolol 2.5 mg (reduced)" · page 2 prose: "continue bisoprolol 5 mg"
? dose: `"CONFLICT: 2.5 mg vs 5 mg"`, flags `["conflict"]`, clarification: "page 1
says 2.5 mg, page 2 says 5 mg — confirm with the clinic"; the item cannot be approved.

**Missing field (never fill in):**
> "Melatonin — take at bedtime as needed for sleep, qty 30" (no dose anywhere)
? dose: `"MISSING"`, flags `["missing_field"]`; do not copy a dose from any other
document or from general knowledge.

**Non-medical rejection:**
> Utility bill with "amount due 21 Dec"
? `is_care_document: false`, zero items; suggest the user may add a household task
manually if they wish.
