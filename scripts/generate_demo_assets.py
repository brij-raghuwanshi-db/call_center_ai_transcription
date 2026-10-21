#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "generated_audio"
SCRIPT_DIR = DATA_DIR / "synthetic_scripts"
KB_DIR = DATA_DIR / "knowledge_base"

TARGET_SR = 16000
TARGET_SEC = 60.0


@dataclass(frozen=True)
class Utterance:
    speaker: str
    text: str
    voice: str
    rate_wpm: int
    gain: float = 0.85


SCENARIOS: dict[str, dict] = {
    "appointment_retention": {
        "title": "Appointment Retention",
        "patient": "Maria Johnson",
        "intent": "appointment_retention",
        "segments": [
            ("Agent", "Thank you for calling Call Center, this is Ava. How can I help today?"),
            ("Patient", "I think I need to cancel my follow-up appointment. I cannot keep missing work."),
            ("Agent", "I understand. Missing work is stressful. Can I ask what time windows are easiest for you?"),
            ("Patient", "Early morning might work, but I am not sure the appointment is even worth it."),
            ("Agent", "Your follow-up helps the care team catch issues early. I can look for an earlier slot and confirm transportation options."),
            ("Patient", "If you can find something before work, I would probably keep it."),
        ],
    },
    "medication_concern": {
        "title": "Medication Concern",
        "patient": "Robert Ellis",
        "intent": "medication_concern",
        "segments": [
            ("Agent", "Thank you for calling Call Center. What medication question can I help route today?"),
            ("Patient", "This new medicine makes me dizzy. I am thinking about stopping it."),
            ("Agent", "I am sorry that is happening. Please do not stop a prescribed medication without clinical guidance."),
            ("Patient", "I just feel off and I do not know if that is normal."),
            ("Agent", "I can connect you with a nurse to review symptoms and next steps. Are you having trouble breathing or chest pain?"),
            ("Patient", "No chest pain, but I would like to talk with a nurse."),
        ],
    },
    "billing_confusion": {
        "title": "Billing Confusion",
        "patient": "Denise Walker",
        "intent": "billing_confusion",
        "segments": [
            ("Agent", "Call Center, this is Ava. How can I help you today?"),
            ("Patient", "I got a bill I do not understand. If this is how it works, I am done with these visits."),
            ("Agent", "I hear how frustrating that is. Let us separate the billing question from the care you still need."),
            ("Patient", "Nobody explained why I owe this much."),
            ("Agent", "I can route the billing review and keep your care plan moving while that is checked."),
            ("Patient", "Okay, I just do not want to be surprised again."),
        ],
    },
    "symptom_escalation": {
        "title": "Symptom Escalation",
        "patient": "James Miller",
        "intent": "symptom_escalation",
        "segments": [
            ("Agent", "Thank you for calling Call Center. Tell me what is going on today."),
            ("Patient", "My chest feels tight and I have been short of breath since this morning."),
            ("Agent", "I am sorry you are feeling that. Because you mentioned chest tightness and shortness of breath, I need to escalate this right away."),
            ("Patient", "I was hoping it would pass, but it is getting worse."),
            ("Agent", "If symptoms are severe or worsening, please call emergency services now. I can also get a nurse on the line immediately."),
            ("Patient", "Please get the nurse. I am scared."),
        ],
    },
    "care_navigation": {
        "title": "Care Navigation",
        "patient": "Linda Chen",
        "intent": "care_navigation",
        "segments": [
            ("Agent", "Call Center, this is Ava. What can I help with?"),
            ("Patient", "I was discharged yesterday and I do not know who I am supposed to call next."),
            ("Agent", "I can help organize the next step. Do you have your discharge paperwork nearby?"),
            ("Patient", "Yes, but it is confusing."),
            ("Agent", "No problem. We can confirm your follow-up appointment, medication questions, and who to call if symptoms change."),
            ("Patient", "That would help a lot."),
        ],
    },
}


KNOWLEDGE_DOCS = {
    "appointment_retention_playbook": "When a patient wants to cancel, acknowledge the barrier, ask about scheduling or transportation constraints, and offer a concrete alternative before ending the call.",
    "medication_concern_handling": "If a patient reports side effects or wants to stop medication, advise them not to discontinue prescribed therapy without clinician direction and offer nurse or pharmacist escalation.",
    "billing_confusion_deescalation": "For billing frustration, validate the concern, route billing review, and reinforce that care continuity should not pause while the billing issue is investigated.",
    "symptom_escalation_triage": "Chest tightness, chest pain, severe shortness of breath, fainting, or rapidly worsening symptoms require urgent escalation to nurse triage or emergency services guidance.",
    "care_navigation_workflow": "For post-discharge confusion, confirm the follow-up appointment, medication questions, warning signs, and the correct contact path for symptom changes.",
    "hipaa_safe_communication": "Before discussing protected health details, verify identity using approved identifiers and avoid unnecessary disclosure of sensitive information.",
}


def clamp_i16(value: int) -> int:
    return max(-32768, min(32767, value))


def write_wav(path: Path, samples: array) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(TARGET_SR)
        wf.writeframes(samples.tobytes())


def read_wav(path: Path) -> array:
    with wave.open(str(path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    out = array("h")
    out.frombytes(frames)
    return out


def render_with_say(text: str, voice: str, rate_wpm: int, tmp_base: Path) -> array | None:
    if not Path("/usr/bin/say").exists() or not Path("/usr/bin/afconvert").exists():
        return None
    aiff = tmp_base.with_suffix(".aiff")
    wav = tmp_base.with_suffix(".wav")
    try:
        subprocess.run(["/usr/bin/say", "-v", voice, "-r", str(rate_wpm), "-o", str(aiff), text], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", f"LEI16@{TARGET_SR}", "-c", "1", str(aiff), str(wav)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return read_wav(wav)
    except Exception:
        return None
    finally:
        for path in (aiff, wav):
            try:
                path.unlink()
            except OSError:
                pass


def render_tone_placeholder(text: str, speaker: str) -> array:
    duration = max(1.4, min(7.5, len(text.split()) * 0.34))
    frequency = 220 if speaker == "Agent" else 175
    samples = array("h")
    for i in range(int(duration * TARGET_SR)):
        envelope = min(1.0, i / (0.08 * TARGET_SR), (duration * TARGET_SR - i) / (0.08 * TARGET_SR))
        value = int(math.sin(2 * math.pi * frequency * i / TARGET_SR) * 2800 * envelope)
        samples.append(clamp_i16(value))
    return samples


def mix(dst: array, src: array, start: int, gain: float) -> None:
    end = min(len(dst), start + len(src))
    for i in range(start, end):
        dst[i] = clamp_i16(dst[i] + int(src[i - start] * gain))


def generate_audio() -> list[dict]:
    random.seed(17)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    metadata: list[dict] = []
    tmp_dir = AUDIO_DIR / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for scenario_id, scenario in SCENARIOS.items():
        output = array("h", [0]) * int(TARGET_SR * TARGET_SEC)
        cursor = int(0.8 * TARGET_SR)
        segments_meta = []
        for idx, (speaker, text) in enumerate(scenario["segments"]):
            voice = "Samantha" if speaker == "Agent" else "Alex"
            rate = 178 if speaker == "Agent" else 160
            rendered = render_with_say(text, voice, rate, tmp_dir / f"{scenario_id}_{idx}")
            if rendered is None:
                rendered = render_tone_placeholder(text, speaker)
            start = cursor
            mix(output, rendered, start, 0.88)
            end = min(len(output), start + len(rendered))
            segments_meta.append({"index": idx, "speaker": speaker, "text": text, "start_ms": int(start / TARGET_SR * 1000), "end_ms": int(end / TARGET_SR * 1000)})
            cursor = end + int(random.uniform(0.25, 0.7) * TARGET_SR)
        noise = array("h", [0]) * len(output)
        y = 0.0
        for i in range(len(noise)):
            y = 0.996 * y + 0.004 * random.gauss(0, 500)
            noise[i] = int(y)
            output[i] = clamp_i16(output[i] + noise[i])
        wav_path = AUDIO_DIR / f"{scenario_id}.wav"
        write_wav(wav_path, output)
        script_payload = {**scenario, "scenario_id": scenario_id, "audio_path": str(wav_path.relative_to(ROOT)), "segments": segments_meta}
        (SCRIPT_DIR / f"{scenario_id}.json").write_text(json.dumps(script_payload, indent=2), encoding="utf-8")
        metadata.append(script_payload)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    (SCRIPT_DIR / "index.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def pdf_bytes(title: str, body: str) -> bytes:
    text = f"{title}\\n\\n{body}".replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 740 Td 14 TL ({text[:1800]}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode('latin-1'))} >> stream\n{stream}\nendstream endobj",
    ]
    content = "%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(content.encode("latin-1")))
        content += obj + "\n"
    xref_offset = len(content.encode("latin-1"))
    content += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        content += f"{offset:010d} 00000 n \n"
    content += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    return content.encode("latin-1")


def generate_knowledge_base() -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for slug, body in KNOWLEDGE_DOCS.items():
        title = slug.replace("_", " ").title()
        txt_path = KB_DIR / f"{slug}.txt"
        pdf_path = KB_DIR / f"{slug}.pdf"
        txt_path.write_text(f"{title}\n\n{body}\n", encoding="utf-8")
        pdf_path.write_bytes(pdf_bytes(title, body))
        rows.append({"document_id": slug, "title": title, "txt_path": str(txt_path.relative_to(ROOT)), "pdf_path": str(pdf_path.relative_to(ROOT)), "content": body})
    (KB_DIR / "documents.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def main() -> int:
    generate_audio()
    generate_knowledge_base()
    print(f"Generated demo assets under {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
