import requests

with open("apikey.txt", "r", encoding="utf-8") as f:
    api_key = f.read()

headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}  # Define python requests headers.
willma_base_url = "https://willma.surf.nl/api/v0"
audio_filename = "./output.wav"
with open(audio_filename, "rb") as f:
    file_bytes = f.read()
headers = {"X-API-KEY": api_key}

response = requests.post(
    f"{willma_base_url}/audio/transcriptions-plus",
    data={
        "model": "Whisper V3 + Diarization",
        "do_diarization": True,
        "chunk_length_s": 25,
        "batch_size": 24,
    },
    files={
        "file": ("audio.wav", file_bytes, "audio/wav")
    },
    headers=headers
)

# --- HANDLE RESPONSE ---
try:
    result = response.json()
except Exception:
    print("Failed to parse JSON:")
    print(response)
    print(response.text)
    exit()

print(result)

transcription_chunks = result["message"]["transcription"]["chunks"]
diarization_raw = result["message"]["diarization"]

# --- PARSE DIARIZATION BLOCK ---
def parse_diarization(diarization_str):
    segments = []
    for line in diarization_str.strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 7 and parts[0] == "SPEAKER":
            try:
                start = float(parts[3])
                duration = float(parts[4])
                # Look for first part starting with SPEAKER_
                speaker = next((p for p in parts if p.startswith("SPEAKER_")), "<NA>")
                segments.append({
                    "start": start,
                    "end": start + duration,
                    "speaker": speaker
                })
            except Exception as e:
                print("Error parsing line:", line)
                print("Error:", e)
    return segments

diarization_segments = parse_diarization(diarization_raw)

print("\nRAW:")
print(result)

# --- LABEL CHUNKS WITH SPEAKERS ---
def label_transcription_chunks(chunks, diarization):
    labeled = []
    for chunk in chunks:
        start, end = chunk["timestamp"]
        text = chunk["text"]
        speaker = "UNKNOWN"

        # Look for overlapping diarization segment
        for seg in diarization:
            if seg["start"] <= end and seg["end"] >= start:
                speaker = seg["speaker"]
                break

        labeled.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text
        })
    return labeled

labeled_transcript = label_transcription_chunks(transcription_chunks, diarization_segments)

from datetime import timedelta

def format_timestamp(seconds: float) -> str:
    """Format seconds to (M:SS) format."""
    td = timedelta(seconds=round(seconds))
    minutes = td.seconds // 60
    seconds = td.seconds % 60
    return f"({minutes}:{seconds:02})"

print("\nSpeaker-Labeled Transcript with Timecodes\n" + "=" * 60)

current_speaker = None
current_block = []

for entry in labeled_transcript:
    speaker = entry["speaker"]
    text = entry["text"].strip()
    start = entry.get("start", 0.0)
    timestamp = format_timestamp(start)

    if speaker != current_speaker:
        # Flush previous block
        if current_block:
            print(f"\n{current_speaker}")
            print(" ".join(current_block))
            current_block = []

        current_speaker = speaker

    current_block.append(f"{timestamp} {text}")

# Flush final block
if current_block:
    print(f"\n{current_speaker}")
    print(" ".join(current_block))

