from flask import Flask, request, render_template_string, redirect, url_for
import subprocess
import time

app = Flask(__name__)

ffplay_process = None
last_url = None
last_title = None
last_thumbnail = None
last_duration = None
start_time = None

HTML = """
<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>🎵 Music Remote</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      background-color: #121212;
      color: #f0f0f0;
      font-family: system-ui, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem;
      text-align: center;
    }
    h1 {
      margin-bottom: 1rem;
      font-size: 2rem;
    }
    form {
      margin: 0.5rem 0;
      width: 100%;
      max-width: 400px;
    }
    .form-group {
      margin-bottom: 0.75rem;
    }
    input[type="text"] {
      width: 100%;
      padding: 0.75rem;
      border-radius: 8px;
      border: none;
      font-size: 1rem;
      box-sizing: border-box;
    }
    button {
      width: 100%;
      padding: 0.75rem;
      border: none;
      border-radius: 8px;
      background-color: #1db954;
      color: white;
      font-size: 1rem;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    button:hover {
      background-color: #1ed760;
    }
    .thumb {
      margin-top: 1rem;
      border-radius: 12px;
      box-shadow: 0 0 12px rgba(0, 0, 0, 0.4);
      width: 100%;
      max-width: 320px;
    }
    .now-playing {
      margin-top: 1.5rem;
      font-size: 1.1rem;
    }
    .progress-container {
      margin-top: 1rem;
      width: 100%;
      max-width: 320px;
    }
    .progress {
      width: 100%;
      height: 8px;
      background-color: #444;
      border-radius: 4px;
      overflow: hidden;
    }
    .progress-bar {
      height: 8px;
      background-color: #1db954;
      width: 0%;
    }
    .time-label {
      margin-top: 0.3rem;
      font-size: 0.9rem;
      color: #ccc;
      display: flex;
      justify-content: space-between;
    }
  </style>
</head>
<body>
  <h1>🎵 Music Remote for OBS</h1>
  <form method="POST" action="/">
    <div class="form-group">
      <input type="text" name="query" placeholder="Zadej název písničky" autofocus required>
    </div>
    <button type="submit">Přehrát</button>
  </form>
  <form method="POST" action="/stop">
    <button style="background-color:#ff4c4c;">🛑 STOP</button>
  </form>
  <form method="POST" action="/play">
    <button style="background-color:#007bff;">▶️ Znovu přehrát</button>
  </form>

  {% if title and thumbnail %}
    <div class="now-playing">Právě hraje: <strong>{{ title }}</strong></div>
    <img src="{{ thumbnail }}" alt="thumbnail" class="thumb">

    {% if duration %}
    <div class="progress-container">
      <div class="progress">
        <div class="progress-bar" id="progressBar"></div>
      </div>
      <div class="time-label">
        <span id="currentTime">0:00</span>
        <span id="totalTime">{{ duration }}</span>
      </div>
    </div>

    <script>
      const startTime = {{ start }};
      const totalSeconds = {{ duration_seconds }};
      function formatTime(s) {
        const m = Math.floor(s / 60);
        const sec = Math.floor(s % 60).toString().padStart(2, '0');
        return m + ":" + sec;
      }
      function updateProgress() {
        const now = Math.floor(Date.now() / 1000);
        const elapsed = now - startTime;
        const progress = Math.min(100, (elapsed / totalSeconds) * 100);
        document.getElementById("progressBar").style.width = progress + "%";
        document.getElementById("currentTime").textContent = formatTime(elapsed);
      }
      setInterval(updateProgress, 1000);
    </script>
    {% endif %}
  {% endif %}
</body>
</html>
"""

import yt_dlp

def get_audio_info(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        entry = info['entries'][0]
        return {
            'url': entry['url'],
            'title': entry['title'],
            'thumbnail': entry.get('thumbnail'),
            'duration': entry.get('duration')  # in seconds
        }

def start_playback(url):
    global ffplay_process, start_time
    stop_playback()
    start_time = int(time.time())
    ffplay_process = subprocess.Popen(
        ['ffplay', '-nodisp', '-autoexit', url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def stop_playback():
    global ffplay_process
    if ffplay_process and ffplay_process.poll() is None:
        ffplay_process.terminate()
        ffplay_process.wait()
    ffplay_process = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global last_url, last_title, last_thumbnail, last_duration, start_time
    if request.method == 'POST':
        query = request.form.get('query')
        if not query:
            return render_template_string(HTML, title=None, thumbnail=None)
        try:
            info = get_audio_info(query)
            last_url = info['url']
            last_title = info['title']
            last_thumbnail = info['thumbnail']
            last_duration = info['duration']
            start_playback(last_url)
            return render_template_string(
                HTML,
                title=last_title,
                thumbnail=last_thumbnail,
                duration=time.strftime('%M:%S', time.gmtime(last_duration)),
                duration_seconds=last_duration,
                start=start_time
            )
        except Exception as e:
            return render_template_string(HTML + f"<p style='color:red;'>Chyba: {e}</p>", title=None, thumbnail=None)
    return render_template_string(
        HTML,
        title=last_title,
        thumbnail=last_thumbnail,
        duration=time.strftime('%M:%S', time.gmtime(last_duration)) if last_duration else None,
        duration_seconds=last_duration,
        start=start_time
    )

@app.route('/stop', methods=['POST'])
def stop():
    stop_playback()
    return redirect(url_for('index'))

@app.route('/play', methods=['POST'])
def play():
    if last_url:
        start_playback(last_url)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7080)
