import requests
import base64
import json

with open("apikey.txt", "r", encoding="utf-8") as f:
    api_key = f.read()
headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}  # Define python requests headers.
willma_base_url = "https://willma.liza.surf.nl/api/v0"
models = requests.get(f"{willma_base_url}/sequences", headers=headers).json()
model = next(filter(lambda x: "whisper" in x.get("name").lower(), models))
audio_filename = "./output.wav"

# We need to read the audio bytes, to be able to send them over network.
with open(audio_filename, "rb") as f:
  audio = f.read()

# Sending raw bytes is not supported over JSON, so we encode them into base64.
b64_audio = base64.b64encode(audio).decode()

response = requests.post(
  f"{willma_base_url}/audio/transcriptions", data=json.dumps(
    {
      "sequence_id": model.get("id"),
      "input": b64_audio,
      "stream": True,
    }
  ), headers=headers, stream=True
)

for b_msg in response.iter_lines():
  msg = b_msg.decode("utf-8")

  if not msg.startswith("data:"):
    continue

  msg = msg[len("data:"):].strip()

  print(msg)