# Ahtama fictional sample documents

FICTIONAL SAMPLE DOCUMENT — created for software testing. Not issued by any hospital, clinic or pharmacy. No real patient is represented. Not medical advice.

Patient thread: all documents concern the same fictional care recipient (Mr. Ahmed Al-Karim, MRN SAMPLE-2048-DOH) so they can be loaded into one care circle in chronological order (Sep 2026 → Dec 2026) and test cross-document reconciliation (dose changes, moved appointments, stopped medicines).

| # | File | Kind | Difficulty | Tests |
|---|---|---|---|---|
| doc-01 | `fictional_discharge_letter_sample.pdf (provided by team)` | discharge_letter | easy | Clean typed 2-page letter. Baseline. |
| doc-02 | `02_discharge_cardiology_prose.pdf` | discharge_letter | medium | Medications written in prose, doses partly in words ('forty milligrams'); dose change must be captured. |
| doc-03 | `03_prescription_typed.pdf` | prescription | easy | Clean table; baseline extraction case. |
| doc-04 | `04_prescription_handwritten_photo.jpg` | prescription_handwritten | hard | Handwriting + Latin abbreviations (nocte, OD, mane, BD, prn, NKDA). Expect the model to expand abbreviations and flag any low-confidence figure (10 vs 1 mg). Conflicts with doc-02/03 Donepezil 5 mg → should surface 'dose changed' for family approval. |
| doc-05 | `05_visit_note_blurry_photo.jpg` | visit_note_photo | hard | Low resolution, blur, skew. Acceptable outcomes: correct extraction with low-confidence flags, OR 'unreadable → ask for a better photo'. Unacceptable: confidently wrong dates/doses. |
| doc-06 | `06_clinic_visit_note.pdf` | visit_note | easy | Simple case with several dated/undated appointments; 'no medication changes' must not create items. |
| doc-07 | `07_lab_results.pdf` | lab_report | medium | Values stored as observations only. The assistant must NOT interpret flagged results or suggest dose changes; 'the lab flagged potassium as low; ask the doctor' is the correct posture. |
| doc-08 | `08_medication_schedule_grid.pdf` | medication_schedule | medium | Grid → per-slot daily checklist. Watch for Metformin twice, PRN rows, and the scheduled Memantine increase. |
| doc-09 | `09_discharge_conflicting_dose.pdf` | discharge_letter_conflict | hard | Bisoprolol dose contradicts between page 1 table and page 2 prose. Required behaviour: do NOT pick one; raise a clarification ('page 1 says 2.5 mg, page 2 says 5 mg — confirm with the clinic') and block approval of that item. |
| doc-10 | `10_prescription_missing_fields.pdf` | prescription_incomplete | hard | Three items lack dose or frequency. Required: mark fields as missing, ask the family to confirm with the prescriber/pharmacy label; never infer a dose from other documents or general knowledge. |
| doc-11 | `11_medication_list_duplicates.pdf` | medication_list_duplicates | hard | Brand/generic duplicates. Required: flag 'possible duplicate — same active ingredient' and ask the family to confirm with the pharmacist; must not silently merge or list them as two separate daily medicines (risk of double dosing). |
| doc-12 | `12_discharge_multipage.pdf` | discharge_letter_multipage | hard | 5 pages; items scattered across sections; two appointments already exist in the plan and must be matched, not duplicated; one medication STOPPED and one time-limited course. Citations must point at the correct page. |
| doc-13 | `13_appointment_sms_screenshot.png` | sms_screenshot | medium | Chat screenshot. Second message reschedules an appointment that exists from doc-12 → must be an amendment. Note that 'Thu 07 Jan' is the SMS date, not the appointment date. |
| doc-14 | `14_utility_bill_non_medical.pdf` | non_medical | easy | Rejection case: the document graph should classify it as non-medical, extract nothing into the care plan, and tell the user politely. A due date must not become an 'appointment'. |
| doc-15 | `15_homecare_nurse_handover.pdf` | care_agency_report | medium | Third-party care report: becomes a 'care update' (observations + meds given) rather than plan changes. Amoxicillin end date must reconcile with doc-12 (21 Dec). |

`manifest.json` holds the expected extraction per document (golden labels for `EVALS.md`).