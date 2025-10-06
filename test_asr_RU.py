#!/usr/bin/env python3
import clam.common.client
import clam.common.data
import clam.common.status
import random
import sys
import os
import time
from getpass import getpass
from pathlib import Path

# ==========================================================
# Interactive user prompts
# ==========================================================
print("🎙️  CLS ASR Diarization + Transcription Client\n")

auth_mode = input("Authentication method — [1] Basic (username/password) or [2] OAuth2 token? (1/2): ").strip() or "1"

clam_url = "https://webservices2.cls.ru.nl/asrservice"

clamclient = None
if auth_mode == "2":
    # OAuth2
    oauth_access_token = getpass("OAuth2 access token (hidden): ").strip()
    clamclient = clam.common.client.CLAMClient(
        clam_url,
        oauth=True,
        oauth_access_token=oauth_access_token,
    )
else:
    # HTTP Basic Auth
    username = input("Username: ").strip()
    password = getpass("Password: ").strip()
    clamclient = clam.common.client.CLAMClient(
        clam_url,
        username,
        password,
        basicauth=True,
    )

# ==========================================================
# Collect job parameters
# ==========================================================
file_path = input("Path to WAV file (e.g. ./audio.wav): ").strip()
if not file_path.lower().endswith(".wav") or not os.path.exists(file_path):
    print("Invalid file: must be an existing .wav file.")
    sys.exit(1)

language = input("Language (nl/en/de/fr/it/ja/zh/es/pt/uk) [default=en]: ").strip() or "en"
model = input("Model (tiny/small/medium/large/large-v2/large-v3) [default=large-v3]: ").strip() or "large-v3"

gpu_input = input("Use GPU? (y/n) [default=y]: ").strip().lower() or "y"
gpu = True if gpu_input in ["y", "yes"] else False

diarization_input = input("Enable diarization? (y/n) [default=y]: ").strip().lower() or "y"
diarization = True if diarization_input in ["y", "yes"] else False

minspeakers = input("Minimum speakers (default 1): ").strip()
maxspeakers = input("Maximum speakers (default 2): ").strip()
minspeakers = int(minspeakers) if minspeakers.isdigit() else 1
maxspeakers = int(maxspeakers) if maxspeakers.isdigit() else 2

project_name = input("Project name (for output file naming): ").strip() or "default"
inputtemplate = "InputWavFile"

# ==========================================================
# Create project and upload file
# ==========================================================
project = f"{project_name}_{random.getrandbits(32)}"

print(f"\n🔗 Connecting to ASR service at {clam_url}")
print(f"🆕 Creating project: {project}")

try:
    clamclient.create(project)
except Exception as e:
    print(f"Failed to create project: {e}")
    sys.exit(1)

data = clamclient.get(project)

print("Uploading audio file...")
clamclient.addinputfile(project, data.inputtemplate(inputtemplate), file_path)

# ==========================================================
# Start transcription
# ==========================================================
print("🚀 Starting transcription...")
try:
    data = clamclient.startsafe(
        project,
        language=language,
        model=model,
        gpu=gpu,
        diarization=diarization,
        minspeakers=minspeakers,
        maxspeakers=maxspeakers,
    )
except Exception as e:
    print(f"Failed to start processing: {e}")
    clamclient.delete(project)
    sys.exit(1)

if data.errors:
    print("Parameter error:")
    print(data.errormsg)
    for parametergroup, paramlist in data.parameters:
        for parameter in paramlist:
            if parameter.error:
                print(f"  - {parameter.id}: {parameter.error}")
    clamclient.delete(project)
    sys.exit(1)

# ==========================================================
# Poll for completion
# ==========================================================
print("⏳ Processing... (this can take a while)")
while data.status != clam.common.status.DONE:
    time.sleep(5)
    data = clamclient.get(project)
    print(f"   Progress: {data.completion}% — {data.statusmessage}", end="\r")

print("\n Done!")

# ==========================================================
# Download the SRT file
# ==========================================================
output_dir = Path("./output")
output_dir.mkdir(exist_ok=True)

basename = Path(file_path).stem
output_path = output_dir / f"{basename}_{project_name}.srt"

found_srt = False
for outputfile in data.output:
    try:
        outputfile.loadmetadata()
    except:
        continue

    outputtemplate = outputfile.metadata.provenance.outputtemplate_id
    if outputtemplate == "SRT":
        print(f"Downloading SRT file to: {output_path}")
        outputfile.copy(str(output_path))
        found_srt = True
        break

if not found_srt:
    print("No SRT file found in output — available outputs:")
    for of in data.output:
        print(f"  - {of}")

# ==========================================================
# Clean up project remotely
# ==========================================================
print("Cleaning up project on server...")
try:
    clamclient.delete(project)
except Exception:
    print("Could not delete remote project (may not matter).")

print(f"\nAll done! Output saved at: {output_path}\n")
