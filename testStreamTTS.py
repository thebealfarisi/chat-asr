import requests
import subprocess

url = 'https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL/stream'
headers = {
    'accept': '*/*',
    'xi-api-key': 'f50d1be461e8b345177480c5e8ef7b3a',
    'Content-Type': 'application/json'
}
data = {
    'text': 'This is pretty fast huh?! Look at me talking away! doo doo doo.',
    'voice_settings': {
        'stability': 0.50,
        'similarity_boost': 0.30
    }
}

response = requests.post(url, headers=headers, json=data, stream=True)
response.raise_for_status()

# use subprocess to pipe the audio data to ffplay and play it
ffplay_cmd = ['ffplay', '-autoexit', '-']
ffplay_proc = subprocess.Popen(ffplay_cmd, stdin=subprocess.PIPE)
for chunk in response.iter_content(chunk_size=4096):
    ffplay_proc.stdin.write(chunk)
    print("Downloading...")

# close the ffplay process when finished
ffplay_proc.stdin.close()
ffplay_proc.wait()