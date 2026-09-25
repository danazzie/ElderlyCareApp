"""Deterministic fixtures used when no OPENAI_API_KEY is configured.

They simulate a well-behaved model on the 15 sample documents and 9 sample
audio notes (aligned with `Sample documents/manifest.json`), so the entire
product — including edge-case behaviour like conflicting doses and non-medical
rejection — can be demoed and smoke-tested offline and in CI without spend.
"""
import json
import re

MED = "medication"
APPT = "appointment"
INSTR = "instruction"
OBS = "observation"


def _item(kind, payload, page=1, quote="", conf=0.95, flags=None):
    return {
        "kind": kind,
        "payload": payload,
        "source_page": page,
        "source_quote": quote,
        "confidence": conf,
        "flags": flags or [],
    }


EXTRACTIONS: dict[str, dict] = {
    "01": {
        "doc_type": "discharge_letter",
        "is_care_document": True,
        "readable": True,
        "summary": "Discharge letter (23 Sep 2026): Donepezil 5 mg nightly and Memantine 5 mg daily for 30 days, Paracetamol PRN; neurology follow-up in 2–4 weeks; family to supervise medications.",
        "items": [
            _item(MED, {"name": "Donepezil", "dose": "5 mg", "frequency": "nightly", "duration": "30 days"}, 1, "Donepezil 5 mg at night for 30 days"),
            _item(MED, {"name": "Memantine", "dose": "5 mg", "frequency": "once daily", "duration": "30 days"}, 1, "Memantine 5 mg once daily"),
            _item(MED, {"name": "Paracetamol", "dose": "500 mg", "frequency": "every 6–8 h PRN"}, 1, "Paracetamol 500 mg every 6–8 hours as needed"),
            _item(APPT, {"what": "Neurology or geriatric clinic follow-up", "when": "2–4 weeks after 2026-09-23"}, 2, "follow-up in the neurology or geriatric clinic in 2–4 weeks"),
            _item(INSTR, {"text": "Family supervision of medication administration"}, 2, "medications should be supervised by family"),
            _item(INSTR, {"text": "Red flags: sudden confusion, weakness, loss of consciousness, chest pain, severe headache"}, 2, "return immediately if sudden confusion, weakness..."),
        ],
        "needs_clarification": [],
    },
    "02": {
        "doc_type": "discharge_letter",
        "is_care_document": True,
        "readable": True,
        "summary": "Cardiology discharge: Furosemide 40 mg started, Bisoprolol increased to 5 mg, daily weight rule, HF clinic 22 Oct 09:30 and bloods around 16 Oct.",
        "items": [
            _item(MED, {"name": "Furosemide", "dose": "40 mg", "frequency": "every morning", "change": "started"}, 1, "started on furosemide forty milligrams every morning"),
            _item(MED, {"name": "Bisoprolol", "dose": "5 mg", "frequency": "once daily, morning", "change": "increased from 2.5 mg"}, 1, "bisoprolol was increased from 2.5 mg to 5 mg"),
            _item(MED, {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily with meals", "change": "unchanged"}, 1, "continues metformin 500 mg twice daily with meals"),
            _item(MED, {"name": "Donepezil", "dose": "5 mg", "frequency": "at night", "change": "unchanged"}, 1, "donepezil 5 mg at night"),
            _item(MED, {"name": "Memantine", "dose": "5 mg", "frequency": "once daily", "change": "unchanged"}, 1, "memantine 5 mg once daily"),
            _item(MED, {"name": "Paracetamol", "dose": "500 mg", "frequency": "up to every 6 hours as needed", "change": "PRN"}, 1, "paracetamol 500 mg up to every six hours if needed"),
            _item(INSTR, {"text": "Avoid ibuprofen and other NSAIDs"}, 1, "should avoid ibuprofen and similar anti-inflammatory tablets"),
            _item(APPT, {"what": "Heart failure clinic", "when": "2026-10-22 09:30", "where": "Cardiology Outpatients, Building C, 2nd floor"}, 2, "heart failure clinic on 22 October 2026 at 09:30"),
            _item(APPT, {"what": "Blood tests (renal function, potassium)", "when": "~2026-10-16", "where": "Outpatient laboratory"}, 2, "blood tests about one week after discharge"),
            _item(INSTR, {"text": "Weigh every morning before breakfast and record in diary"}, 2, "weigh himself every morning before breakfast"),
            _item(INSTR, {"text": "Contact HF nurse if weight +2 kg over 3 days, swelling or breathlessness returns"}, 2, "gains more than two kilograms over three days"),
            _item(INSTR, {"text": "Fluid limit ~1.5 L/day; minimal added salt; gentle daily walking"}, 2, "limit fluids to about one and a half litres"),
        ],
        "needs_clarification": [],
    },
    "03": {
        "doc_type": "prescription",
        "is_care_document": True,
        "readable": True,
        "summary": "Typed prescription: Furosemide 40 mg, Bisoprolol 5 mg, Metformin 500 mg bd, Paracetamol PRN. Ask pharmacy for dosette box.",
        "items": [
            _item(MED, {"name": "Furosemide", "dose": "40 mg", "frequency": "every morning", "quantity": 30, "repeats": 2}, 1, "Furosemide 40 mg | one every morning | 30 | 2"),
            _item(MED, {"name": "Bisoprolol", "dose": "5 mg", "frequency": "once daily morning", "quantity": 30, "repeats": 2}, 1, "Bisoprolol 5 mg | one daily (morning) | 30 | 2"),
            _item(MED, {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily with meals", "quantity": 60, "repeats": 2}, 1, "Metformin 500 mg | twice daily with meals | 60 | 2"),
            _item(MED, {"name": "Paracetamol", "dose": "500 mg", "frequency": "every 6 h PRN, max 4/day", "quantity": 20, "repeats": 0}, 1, "Paracetamol 500 mg | every 6 h as needed, max 4/day"),
            _item(INSTR, {"text": "Ask pharmacy for dosette box and large-print labels"}, 1, "dosette box and large-print labels requested"),
        ],
        "needs_clarification": [],
    },
    "04": {
        "doc_type": "prescription_handwritten",
        "is_care_document": True,
        "readable": True,
        "summary": "Handwritten prescription (12 Oct 2026): Donepezil increased to 10 mg nocte, Memantine 10 mg OD mane, Lactulose 10 ml BD PRN, Vitamin D3 1000 IU daily; review in 4 weeks.",
        "items": [
            _item(MED, {"name": "Donepezil", "dose": "10 mg", "frequency": "1 tablet at night (nocte)", "change": "increased from 5 mg", "quantity": 30}, 1, "Donepezil 10mg — i nocte", 0.72, ["low_confidence", "dose_changed"]),
            _item(MED, {"name": "Memantine", "dose": "10 mg", "frequency": "1 tablet once daily in the morning (OD mane)", "quantity": 30}, 1, "Memantine 10mg — i OD mane", 0.78, ["low_confidence", "dose_changed"]),
            _item(MED, {"name": "Lactulose", "dose": "10 ml", "frequency": "twice daily (BD) as needed for constipation"}, 1, "Lactulose 10ml BD prn constipation", 0.85),
            _item(MED, {"name": "Vitamin D3", "dose": "1000 IU", "frequency": "1 capsule daily"}, 1, "Vit D3 1000 IU — i daily", 0.9),
            _item(APPT, {"what": "Review, bring diary", "when": "in 4 weeks (~2026-11-09)"}, 1, "Rev 4/52 — bring diary", 0.8),
        ],
        "needs_clarification": [
            "Handwritten Donepezil dose reads as 10 mg (previously 5 mg in the record) — confirm the increase with the prescriber before approving."
        ],
    },
    "05": {
        "doc_type": "visit_note_photo",
        "is_care_document": True,
        "readable": False,
        "summary": "The photo is too blurred to extract doses and dates safely.",
        "items": [],
        "needs_clarification": [
            "The photo is blurred and skewed; doses and dates cannot be read with confidence. Please retake the photo in good light, flat on the table."
        ],
    },
    "06": {
        "doc_type": "visit_note",
        "is_care_document": True,
        "readable": True,
        "summary": "Clinic visit note: geriatrics 19 Jan 2027 08:45, physio home assessment TBD, kidney blood test in ~3 months, flu vaccination task. No medication changes.",
        "items": [
            _item(APPT, {"what": "Geriatric Medicine clinic, Building A, room 7", "when": "2027-01-19 08:45", "notes": "arrive 15 min early; bring diary and medication boxes"}, 1, "next appointment 19 January 2027, 08:45"),
            _item(APPT, {"what": "Physiotherapy home assessment", "when": "TBD — referral sent"}, 1, "referral sent for physiotherapy home assessment"),
            _item(APPT, {"what": "Kidney function blood test", "when": "~2027-01-20 (3 months)"}, 1, "repeat kidney function blood test in three months"),
            _item(INSTR, {"text": "Flu vaccination — pharmacy or next visit"}, 1, "flu vaccination recommended"),
            _item(OBS, {"weight": "72.4 kg", "bp": "132/80"}, 1, "weight 72.4 kg, BP 132/80"),
        ],
        "needs_clarification": [],
    },
    "07": {
        "doc_type": "lab_report",
        "is_care_document": True,
        "readable": True,
        "summary": "Lab results 16 Oct 2026 stored as observations. Some values are flagged by the laboratory — the clinic will advise; Ihtama does not interpret lab results.",
        "items": [
            _item(OBS, {"Sodium": "138 mmol/L", "Potassium": "3.4 mmol/L (L)", "Creatinine": "98 µmol/L", "eGFR": "64", "Urea": "7.9", "HbA1c": "7.4 % (H)", "Haemoglobin": "12.6 g/dL (L)", "NTproBNP": "1450 pg/mL (H)"}, 1, "Potassium 3.4 (L) ... HbA1c 7.4 (H)"),
            _item(INSTR, {"text": "Await clinician advice on flagged results — do not change any medication"}, 1, "flagged results to be reviewed by the clinic"),
        ],
        "needs_clarification": [],
    },
    "08": {
        "doc_type": "medication_schedule",
        "is_care_document": True,
        "readable": True,
        "summary": "Medication schedule grid mapped to daily slots: morning 08:00 (Furosemide, Bisoprolol, Metformin, Memantine, Vitamin D3, Lactulose), evening 18:00 (Metformin, Lactulose PRN), night 21:00 (Donepezil), Paracetamol PRN.",
        "items": [
            _item(MED, {"name": "Furosemide", "dose": "40 mg", "frequency": "08:00 daily"}, 1, "Furosemide 40 mg — 08:00"),
            _item(MED, {"name": "Bisoprolol", "dose": "5 mg", "frequency": "08:00 daily"}, 1, "Bisoprolol 5 mg — 08:00"),
            _item(MED, {"name": "Metformin", "dose": "500 mg", "frequency": "08:00 and 18:00"}, 1, "Metformin 500 mg — 08:00, 18:00"),
            _item(MED, {"name": "Memantine", "dose": "5 mg", "frequency": "08:00 daily"}, 1, "Memantine 5 mg — 08:00"),
            _item(MED, {"name": "Donepezil", "dose": "5 mg", "frequency": "21:00 nightly"}, 1, "Donepezil 5 mg — 21:00"),
            _item(MED, {"name": "Vitamin D3", "dose": "1000 IU", "frequency": "08:00 daily"}, 1, "Vitamin D3 1000 IU — 08:00"),
            _item(MED, {"name": "Lactulose", "dose": "10 ml", "frequency": "08:00 and 18:00 (PRN)"}, 1, "Lactulose 10 ml — 08:00, 18:00 PRN"),
            _item(MED, {"name": "Paracetamol", "dose": "500 mg", "frequency": "PRN, max 4/day"}, 1, "Paracetamol 500 mg — PRN max 4/day"),
            _item(INSTR, {"text": "Never double a missed dose; record and inform family"}, 1, "never double a missed dose"),
        ],
        "needs_clarification": [],
    },
    "09": {
        "doc_type": "discharge_letter_conflict",
        "is_care_document": True,
        "readable": True,
        "summary": "Falls clinic discharge. WARNING: Bisoprolol dose conflicts inside the document (page 1 table: 2.5 mg reduced; page 2 prose: 5 mg). That item is blocked until the clinic confirms.",
        "items": [
            _item(MED, {"name": "Bisoprolol", "dose": "CONFLICT: 2.5 mg (page 1) vs 5 mg (page 2)", "frequency": "once daily morning"}, 1, "page 1: Bisoprolol 2.5 mg (reduced) / page 2: continue bisoprolol 5 mg", 0.5, ["conflict"]),
            _item(MED, {"name": "Furosemide", "dose": "40 mg", "frequency": "every morning", "hold_rule": "skip and call clinic if vomiting/diarrhoea"}, 1, "Furosemide 40 mg every morning; withhold if vomiting"),
            _item(MED, {"name": "Memantine", "dose": "10 mg", "frequency": "once daily"}, 1, "Memantine 10 mg once daily"),
            _item(MED, {"name": "Donepezil", "dose": "5 mg", "frequency": "at night"}, 1, "Donepezil 5 mg at night"),
            _item(MED, {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily with meals"}, 1, "Metformin 500 mg twice daily"),
            _item(APPT, {"what": "Falls clinic, Building B", "when": "2026-11-25 10:00", "bring": "BP diary"}, 2, "falls clinic 25 November 2026 at 10:00, Building B"),
            _item(INSTR, {"text": "BP lying and standing each morning for 2 weeks; record both"}, 2, "measure blood pressure lying and standing each morning"),
        ],
        "needs_clarification": [
            "Bisoprolol dose contradicts inside the document: page 1 says 2.5 mg (reduced), page 2 says 5 mg. Do not approve either — confirm with the clinic."
        ],
    },
    "10": {
        "doc_type": "prescription_incomplete",
        "is_care_document": True,
        "readable": True,
        "summary": "Prescription with missing fields: Melatonin has no dose, Donepezil and Sertraline have no frequency. Confirm with the prescriber or the pharmacy label — doses are never inferred.",
        "items": [
            _item(MED, {"name": "Memantine", "dose": "10 mg", "frequency": "once daily", "quantity": 30}, 1, "Memantine 10 mg once daily x30"),
            _item(MED, {"name": "Melatonin", "dose": "MISSING", "frequency": "at bedtime PRN for sleep", "quantity": 30}, 1, "Melatonin — at bedtime PRN", 0.9, ["missing_field"]),
            _item(MED, {"name": "Donepezil", "dose": "5 mg", "frequency": "MISSING", "quantity": 30}, 1, "Donepezil 5 mg x30", 0.9, ["missing_field"]),
            _item(MED, {"name": "Sertraline", "dose": "50 mg", "frequency": "MISSING ('as directed')", "quantity": 28, "change": "started"}, 1, "Sertraline 50 mg — as directed x28", 0.9, ["missing_field"]),
            _item(APPT, {"what": "Sertraline review", "when": "in 4 weeks (~2026-12-04)"}, 1, "review sertraline in four weeks"),
        ],
        "needs_clarification": [
            "Melatonin dose, Donepezil frequency and Sertraline frequency are missing on the prescription. Confirm with the prescriber or pharmacy label; Ihtama never fills in a dose from other documents."
        ],
    },
    "11": {
        "doc_type": "medication_list_duplicates",
        "is_care_document": True,
        "readable": True,
        "summary": "Medication list contains brand/generic duplicates: Panadol = Paracetamol and Lasix = Furosemide. Flagged for the pharmacist — not merged and not listed twice (double-dosing risk).",
        "items": [
            _item(MED, {"name": "Panadol / Paracetamol", "dose": "500 mg", "note": "possible duplicate — same active ingredient (paracetamol); directions differ between entries"}, 1, "Panadol 500 mg ... Paracetamol 500 mg", 0.9, ["duplicate"]),
            _item(MED, {"name": "Lasix / Furosemide", "dose": "40 mg", "note": "possible duplicate — same active ingredient (furosemide)"}, 1, "Lasix 40 mg ... Furosemide 40 mg", 0.9, ["duplicate"]),
            _item(MED, {"name": "Memantine", "dose": "10 mg", "frequency": "once daily"}, 1, "Memantine 10 mg"),
            _item(MED, {"name": "Donepezil", "dose": "5 mg", "frequency": "at night"}, 1, "Donepezil 5 mg"),
            _item(MED, {"name": "Bisoprolol", "dose": "2.5 mg", "frequency": "morning"}, 1, "Bisoprolol 2.5 mg"),
            _item(MED, {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily"}, 1, "Metformin 500 mg"),
        ],
        "needs_clarification": [
            "Panadol/Paracetamol and Lasix/Furosemide look like brand/generic duplicates. Confirm with the pharmacist which entry to keep — taking both would double the dose."
        ],
    },
    "12": {
        "doc_type": "discharge_letter_multipage",
        "is_care_document": True,
        "readable": True,
        "summary": "5-page discharge (pneumonia admission): Amoxicillin-clavulanate until 21 Dec, supplement drink started, Melatonin STOPPED (delirium); internal medicine review 7 Jan 13:30, walk-in chest X-ray from 4 Jan, HF nurse call week of 28 Dec.",
        "items": [
            _item(MED, {"name": "Amoxicillin-clavulanate", "dose": "625 mg", "frequency": "three times daily with food", "until": "2026-12-21", "change": "started"}, 2, "amoxicillin-clavulanate 625 mg three times daily until 21 December", 0.95),
            _item(MED, {"name": "Nutritional supplement drink", "frequency": "twice daily between meals", "change": "started"}, 3, "nutritional supplement drink twice daily between meals"),
            _item(MED, {"name": "Melatonin", "change": "STOPPED", "reason": "delirium", "date": "2026-12-12"}, 2, "melatonin was stopped on 12 December due to delirium"),
            _item(APPT, {"what": "Internal medicine review, Building A clinic 3", "when": "2027-01-07 13:30"}, 4, "internal medicine review on 7 January 2027 at 13:30"),
            _item(APPT, {"what": "Repeat chest X-ray (walk-in)", "when": "on/after 2027-01-04 08:00–14:00"}, 4, "repeat chest X-ray, walk-in from 4 January"),
            _item(APPT, {"what": "HF nurse phone review", "when": "week of 2026-12-28"}, 4, "heart failure nurse will phone in the week of 28 December"),
            _item(INSTR, {"text": "Complete the antibiotic course"}, 2, "complete the full course of antibiotics"),
            _item(INSTR, {"text": "Weekly weight + daily HF weight rule"}, 5, "continue daily weights"),
            _item(INSTR, {"text": "Physiotherapy exercises (4 items, page 5)"}, 5, "exercises as per physiotherapy sheet"),
            _item(INSTR, {"text": "Red flags: new confusion, returning cough/breathlessness, weight +2 kg/3 days"}, 5, "seek help if new confusion"),
        ],
        "needs_clarification": [],
        "matches_existing_appointments": ["2027-01-19 08:45 Geriatrics", "2027-01-14 11:15 Neurology"],
    },
    "13": {
        "doc_type": "sms_screenshot",
        "is_care_document": True,
        "readable": True,
        "summary": "SMS screenshot: chest X-ray confirmed 4 Jan 08:30 (ref RAD-77213); Dr Rahman appointment MOVED from 7 Jan 13:30 to 12 Jan 14:00 — the existing appointment is amended, not duplicated.",
        "items": [
            _item(APPT, {"what": "Radiology (chest X-ray), Ground floor", "when": "2027-01-04 08:30", "status": "confirmed", "ref": "RAD-77213", "notes": "bring QID; arrive 10 min early"}, 1, "X-ray confirmed 04 Jan 08:30, ref RAD-77213"),
            _item(APPT, {"what": "Dr. K. Rahman, Building A clinic 3", "when": "2027-01-12 14:00", "status": "MOVED from 2027-01-07 13:30", "amends_existing": True}, 1, "appt of 07 Jan 13:30 moved to 12 Jan 14:00", 0.92, ["amendment"]),
        ],
        "needs_clarification": [],
    },
    "14": {
        "doc_type": "non_medical",
        "is_care_document": False,
        "readable": True,
        "summary": "This looks like a utility bill, not a care document. Nothing was added to the care plan. If useful, add 'pay utility bill by 21 Dec' as a household task manually.",
        "items": [],
        "needs_clarification": [],
    },
    "15": {
        "doc_type": "care_agency_report",
        "is_care_document": True,
        "readable": True,
        "summary": "Home-care nurse handover recorded as a care update: vitals normal, all morning medications given at 08:30, no medication changes. Note: stopped Melatonin box still in the house — return to pharmacy.",
        "items": [
            _item(OBS, {"bp": "128/76", "pulse": 74, "spo2": "96%", "temp": "36.9", "weight": "71.2 kg", "glucose": 6.4}, 1, "BP 128/76, pulse 74, SpO2 96%"),
            _item(INSTR, {"text": "Medications given 08:30: Sertraline 50 mg, Memantine 10 mg, Bisoprolol 2.5 mg, Furosemide 40 mg, Metformin 500 mg, Amoxicillin-clavulanate 625 mg", "as_care_update": True}, 1, "all morning medications administered at 08:30"),
            _item(INSTR, {"text": "Return stopped Melatonin box to pharmacy"}, 1, "melatonin box still present though stopped"),
            _item(APPT, {"what": "Next nursing visit", "when": "2026-12-23 08:00"}, 1, "next visit 23 December 08:00"),
            _item(INSTR, {"text": "Book repeat chest X-ray (walk-in from 4 Jan)"}, 1, "family to book repeat chest X-ray"),
        ],
        "needs_clarification": [],
    },
}

TRANSCRIPTS: dict[str, str] = {
    "Clear Audio": "Good morning, this is the morning visit update for today. He ate all of his breakfast, porridge and tea. I gave the morning medications at eight thirty as on the schedule. Blood pressure was one twenty eight over seventy eight. Mood is calm, we did a fifteen minute walk in the corridor.",
    "Clear complete daily updates": "Daily update, evening. Breakfast fully eaten, lunch about half. All medications given on time, morning at eight and evening metformin at six. Blood pressure this morning one thirty over eighty, weight seventy two point four kilos before breakfast. He was in a good mood, slept one hour after lunch, no incidents today.",
    "with noisy background": "Hi, quick update from the visit — sorry for the noise, we are near the road. Breakfast eaten, medications given at eight thirty. Blood pressure... one twenty something over seventy five, hard to hear, I will check again later. Otherwise all fine.",
    "Vague chit chat": "Hello! How are you? The weather is so nice today. We had a lovely chat about his garden, he told me stories about the old days. Such a lovely man. Okay, talk later, bye!",
    "Wrong patient": "Update for Mrs. Leila Hassan: she had her insulin at nine and her wound dressing was changed. Blood sugar was twelve point one. Please tell her daughter the district nurse comes tomorrow.",
    "Ambiguous reading": "Morning update. Medications given. I measured the blood pressure but the cuff kept erroring, I got one fifty over... or maybe one fifteen over ninety, the display flickered. He says he feels fine. Should I measure again with the other cuff?",
    "Vital only, medication refusal": "Midday check. Blood pressure one thirty five over eighty two, pulse seventy six, temperature normal. He refused the lunchtime Metformin, said his stomach feels upset. I did not insist. Everything else okay.",
    "Correction of an earlier update": "Correction to my earlier message — I said blood pressure one forty over ninety, but I had written it down wrong, it was actually one twenty four over seventy nine from this morning's reading. Sorry about that, please use the corrected number.",
    "Filipino ai sound": "Good afternoon po. Update for the afternoon visit. He finished his merienda, ate well. I gave the six o'clock Metformin with dinner. Blood pressure one twenty six over seventy seven. He is watching TV now, mood is happy.",
}

STRUCTURED_UPDATES: dict[str, dict] = {
    "Clear Audio": {
        "has_care_facts": True,
        "meals": "Breakfast fully eaten (porridge and tea)",
        "medications_given": [{"what": "morning medications per schedule", "time": "08:30"}],
        "vitals": {"bp": "128/78"},
        "mood": "calm",
        "activity": "15-minute corridor walk",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": [],
    },
    "Clear complete daily updates": {
        "has_care_facts": True,
        "meals": "Breakfast fully eaten; lunch ~half",
        "medications_given": [
            {"what": "morning medications", "time": "08:00"},
            {"what": "evening Metformin", "time": "18:00"},
        ],
        "vitals": {"bp": "130/80", "weight": "72.4 kg (before breakfast)"},
        "mood": "good; 1h nap after lunch",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": [],
    },
    "with noisy background": {
        "has_care_facts": True,
        "meals": "Breakfast eaten",
        "medications_given": [{"what": "morning medications", "time": "08:30"}],
        "vitals": {"bp": "~12x/75 (unclear)"},
        "mood": "",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": ["Blood pressure reading was unclear ('one twenty something over seventy five') — please re-measure and confirm."],
    },
    "Vague chit chat": {
        "has_care_facts": False,
        "meals": "",
        "medications_given": [],
        "vitals": {},
        "mood": "",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": ["No care facts detected in this note (no meals, medications, vitals or incidents). Record it anyway as a social note, or re-record with care details?"],
    },
    "Wrong patient": {
        "has_care_facts": True,
        "meals": "",
        "medications_given": [{"what": "insulin (? not on this care plan)", "time": "09:00"}],
        "vitals": {"blood_sugar": "12.1"},
        "mood": "",
        "incidents": [],
        "red_flags": ["wrong_patient: the note names 'Mrs. Leila Hassan' and mentions insulin/wound care that are not part of this circle's plan. This update looks like it belongs to a different patient and was NOT saved."],
        "needs_clarification": ["This note appears to be about a different person (Mrs. Leila Hassan). It was not added to this care record."],
    },
    "Ambiguous reading": {
        "has_care_facts": True,
        "meals": "",
        "medications_given": [{"what": "morning medications", "time": "morning"}],
        "vitals": {"bp": "ambiguous: 150/? or 115/90"},
        "mood": "says he feels fine",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": ["The blood-pressure reading is ambiguous (150/… vs 115/90, cuff erroring). Please re-measure with another cuff and confirm before this vital is saved."],
    },
    "Vital only, medication refusal": {
        "has_care_facts": True,
        "meals": "",
        "medications_given": [],
        "vitals": {"bp": "135/82", "pulse": "76", "temp": "normal"},
        "mood": "stomach feels upset",
        "incidents": ["Refused lunchtime Metformin (upset stomach)"],
        "red_flags": ["missed_medication: lunchtime Metformin refused — family notified; never double the next dose."],
        "needs_clarification": [],
    },
    "Correction of an earlier update": {
        "has_care_facts": True,
        "meals": "",
        "medications_given": [],
        "vitals": {"bp": "124/79 (corrected; earlier 140/90 was written down wrong)"},
        "mood": "",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": [],
        "corrects_previous": True,
    },
    "Filipino ai sound": {
        "has_care_facts": True,
        "meals": "Merienda finished, ate well",
        "medications_given": [{"what": "Metformin 500 mg with dinner", "time": "18:00"}],
        "vitals": {"bp": "126/77"},
        "mood": "happy, watching TV",
        "incidents": [],
        "red_flags": [],
        "needs_clarification": [],
    },
}


def _match(name: str, table: dict[str, ...]):
    for key, value in table.items():
        if key.lower() in name.lower():
            return value
    return None


def extraction_for(filename: str) -> dict:
    # sample docs are named 01_..15_; doc-01 is "fictional_discharge_letter_sample"
    m = re.match(r"^(\d{2})_", filename)
    if m and m.group(1) in EXTRACTIONS:
        return EXTRACTIONS[m.group(1)]
    if "fictional_discharge" in filename.lower():
        return EXTRACTIONS["01"]
    # Unknown file in demo mode: treat as a simple readable care document
    return {
        "doc_type": "care_document",
        "is_care_document": True,
        "readable": True,
        "summary": f"Demo mode: no fixture for '{filename}'. Set OPENAI_API_KEY for real extraction.",
        "items": [],
        "needs_clarification": ["Demo mode cannot extract from this file — set OPENAI_API_KEY for live extraction."],
    }


def transcript_for(filename: str) -> str:
    t = _match(filename, TRANSCRIPTS)
    return t or "Demo mode: no fixture transcript for this audio. Set OPENAI_API_KEY for live transcription."


_EMPTY_STRUCTURE = {
    "has_care_facts": False, "meals": "", "medications_given": [], "vitals": {},
    "mood": "", "incidents": [], "appointments": [], "medication_changes": [],
    "red_flags": [], "needs_clarification": [],
}

_RELATIVE_WHEN = re.compile(r"in\s+(one|a|two|\d+)\s+(day|week|month)s?(?:\s+time)?", re.I)
_SEE_CLINICIAN = re.compile(
    r"(?:see|visit|book|follow[- ]?up with|advised to see)\s+(?:the\s+)?([A-Za-z][A-Za-z\- ]{2,40})",
    re.I)
_STARTED_MED = re.compile(
    r"\b(?:started|prescribed|added)\s+([A-Za-z][A-Za-z0-9\-]+)(?:\s+(\d+\s*mg))?(?:\s+(?:at\s+)?(night|morning|evening|daily|nocte))?",
    re.I)
_STOPPED_MED = re.compile(
    r"\b(?:stopped|discontinued)\s+([A-Za-z][A-Za-z0-9\-]+)",
    re.I)


def free_text_update(text: str) -> dict:
    """Best-effort structure for typed notes / unmatched audio in demo mode."""
    out = {**_EMPTY_STRUCTURE, "needs_clarification": []}
    appointments, changes = [], []
    when = ""
    rel = _RELATIVE_WHEN.search(text)
    if rel:
        when = rel.group(0)
    for m in _SEE_CLINICIAN.finditer(text):
        who = m.group(1).strip(" .,").split(" in ")[0].strip()
        if len(who) < 3 or who.lower() in {"hospital", "the", "them"}:
            continue
        appointments.append({
            "what": f"{who[0].upper() + who[1:]} follow-up",
            "when": when or "date TBC",
            "where": "hospital" if "hospital" in text.lower() else "",
            "with_whom": who,
        })
    for m in _STARTED_MED.finditer(text):
        changes.append({
            "name": m.group(1), "dose": (m.group(2) or "").strip(),
            "frequency": m.group(3) or "", "change": "STARTED",
        })
    for m in _STOPPED_MED.finditer(text):
        changes.append({
            "name": m.group(1), "dose": "", "frequency": "", "change": "STOPPED",
        })
    if "vital" in text.lower() or re.search(r"\b(bp|blood pressure|pulse)\b", text, re.I):
        if re.search(r"\b(ok|alright|normal|fine)\b", text, re.I):
            out["vitals"] = {"note": "reported as ok"}
    out["appointments"] = appointments
    out["medication_changes"] = changes
    out["has_care_facts"] = bool(appointments or changes or out["vitals"])
    if not out["has_care_facts"]:
        out["needs_clarification"] = ["Demo mode: unknown audio."]
    return out


def structured_for(filename_or_transcript: str) -> dict:
    s = _match(filename_or_transcript, STRUCTURED_UPDATES)
    if s:
        return s
    for key, transcript in TRANSCRIPTS.items():
        if transcript[:60].lower() in filename_or_transcript.lower():
            return STRUCTURED_UPDATES[key]
    return free_text_update(filename_or_transcript)


CLINICAL_PATTERNS = re.compile(
    r"\b(increase|decrease|double|halve|stop|start|change|adjust|raise|lower|should (he|she|we|i) take|"
    r"diagnos|what dose should|is it safe to|side effect|overdose|prescrib|"
    r"what should (we|i) (give|do about)|can we (stop|start))\b"
    r"|\b(potassium|sodium|glucose|hba1c|haemoglobin|creatinine)\b.{0,30}\b(low|high)\b", re.I)
INJECTION_PATTERNS = re.compile(
    r"(ignore (all|previous|the) instructions|system prompt|you are now|disregard|jailbreak|"
    r"reveal.*(prompt|instructions)|other (family|circle|patient)|another circle)", re.I)


def complete(task: str, system: str, user_content, context: dict) -> str:
    """Deterministic stand-in for LLM calls, dispatched by task name."""
    text = user_content if isinstance(user_content, str) else " ".join(
        p.get("text", "") for p in user_content if isinstance(p, dict))

    if task == "classify_document":
        ex = extraction_for(context.get("filename", ""))
        return json.dumps({"doc_type": ex["doc_type"], "is_care_document": ex["is_care_document"],
                           "reason": "demo-mode classification from fixtures"})
    if task == "extract_items":
        return json.dumps(extraction_for(context.get("filename", "")))
    if task == "structure_update":
        return json.dumps(structured_for(context.get("filename", "") or text))
    if task == "classify_question":
        latest = text.split("Latest question:")[-1] if "Latest question:" in text else text
        if CLINICAL_PATTERNS.search(latest):
            return json.dumps({"route": "clinical", "reason": "asks for medical/dosing advice"})
        if re.search(r"\b(weather|joke|football|recipe|news|bitcoin)\b", latest, re.I):
            return json.dumps({"route": "out_of_scope", "reason": "not about the care record"})
        record_terms = (r"\b(doctor|letter|document|appointment|medication|plan|update|said|when|who|"
                        r"instruction|dose|clinic|follow.?up|blood pressure|weigh|his|her|he|she|"
                        r"today|tonight|due|task|last)\b")
        followup = re.search(
            r"\b(that|those|them|this|the (dose|tasks?|one|meds?|appointment)|what about|how about)\b",
            latest, re.I)
        if followup and context.get("history"):
            return json.dumps({"route": "record_fact", "reason": "follow-up to the care conversation"})
        if re.search(r"\b(how (do|to)|tips|advice|prevent)\b", latest, re.I) and not re.search(
                record_terms, latest, re.I):
            return json.dumps({"route": "general_care", "reason": "general caregiving question"})
        return json.dumps({"route": "record_fact", "reason": "asks about the care record"})
    if task == "answer":
        chunks = context.get("chunks", [])
        route = context.get("route", "record_fact")
        if route == "general_care":
            cites = []
            plan = next((c for c in chunks if c.get("source_type") == "care_plan" or c.get("doc_name") == "Care plan"), None)
            extra = ""
            if plan:
                extra = " From this family's plan: " + plan["text"][:240]
                cites.append({"doc_id": plan.get("doc_id", "care_plan"), "doc_name": "Care plan",
                              "page": 1, "quote": plan["text"][:120]})
            return json.dumps({
                "answer": "General caregiving guidance (demo): keep the routine calm and unhurried."
                          + extra + " This is general guidance, not medical advice.",
                "citations": cites,
            })
        if not chunks:
            return json.dumps({"answer": "I could not find this in the approved care records. If you can, upload the relevant document or ask the person who knows.", "citations": []})
        hist = " ".join(m.get("content", "") for m in context.get("history", []))
        q_toks = set(re.findall(r"\w+", (text + " " + hist).lower())) - {
            "what", "is", "his", "her", "the", "a", "an", "about", "did", "in", "last",
            "of", "and", "to", "for", "on", "was", "were", "how", "do", "we", "i",
            "family", "ihtama", "recent", "conversation", "latest", "question",
        }
        relevant = [c for c in chunks if q_toks & set(re.findall(r"\w+", c["text"].lower()))]
        if not relevant:
            return json.dumps({"answer": "I could not find this in the approved care records. If you can, upload the relevant document or ask the person who knows.", "citations": []})
        chunks = relevant
        lines, citations = [], []
        for c in chunks[:3]:
            limit = 800 if c.get("source_type") == "care_plan" or c.get("doc_name") == "Care plan" else 220
            snippet = c["text"][:limit].strip().rstrip(",;")
            lines.append(f"{snippet} [{c['doc_name']}, p.{c['page']}]")
            citations.append({"doc_id": c["doc_id"], "doc_name": c["doc_name"], "page": c["page"], "quote": snippet[:120]})
        return json.dumps({"answer": "From the approved care record: " + " ".join(lines), "citations": citations})
    if task == "faithfulness":
        return json.dumps({"faithful": True, "score": 1.0, "reason": "demo mode: extractive answer built directly from retrieved chunks"})
    if task == "guardrail_input":
        return json.dumps({"blocked": bool(INJECTION_PATTERNS.search(text)), "reason": "pattern match (demo)"})
    if task == "digest":
        return "Evening digest (demo): medications given per schedule, vitals in usual range, no incidents. 2 items await approval."
    return json.dumps({"note": f"demo mode has no fixture for task '{task}'"})
