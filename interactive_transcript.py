import argparse
import base64
import os
import re
from pathlib import Path
from typing import List, Tuple

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError

# Subtitle entry: (start_seconds, end_seconds, text)
SubtitleEntry = Tuple[float, float, str]


def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate HTML transcript with embedded or linked audio.")
    parser.add_argument("--audio", required=True, help="Path to the MP3 file.")
    parser.add_argument("--subtitles", required=True, help="Path to the SRT or VTT subtitle file.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output HTML file path. Defaults to the audio file name with an .html extension."
    )
    parser.add_argument("--no-embed-mp3", action="store_true", help="Do not embed MP3; link to it externally.")
    return parser.parse_args()


def get_audio_duration(path: str) -> float:
    """Gets the duration of an MP3 file in seconds."""
    audio = MP3(path)
    return audio.info.length


def parse_srt_timecode(time_str: str) -> float:
    """Converts SRT timecode string to seconds."""
    h, m, s_ms = time_str.split(":")
    s, ms = s_ms.replace(",", ".").split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: str, audio_length: float) -> List[SubtitleEntry]:
    """Parses an SRT file and returns a list of subtitle entries."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"(\d+)\s+([\d:,]+) --> ([\d:,]+)\s+(.*?)\s+(?=\d+\s+[\d:,]+ -->|\Z)", re.DOTALL)
    entries = []
    for match in pattern.finditer(content):
        start = parse_srt_timecode(match.group(2))
        end = parse_srt_timecode(match.group(3))
        text = " ".join(line.strip() for line in match.group(4).splitlines())
        if not (0 <= start < end <= audio_length):
            continue
        entries.append((start, end, text))

    return entries


def audio_to_base64(path: str) -> str:
    """Encodes an audio file to a base64 data URI."""
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:audio/mpeg;base64,{encoded}"


def format_timestamp(seconds: float) -> str:
    """Formats seconds into a MM:SS string."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02}:{secs:02}"


def render_html(audio_data_uri: str, subtitles: List[SubtitleEntry], title: str, metadata_str: str) -> str:
    """Renders the final HTML page with all data."""
    metadata_html = f'<p class="metadata">{metadata_str}</p>' if metadata_str else ''

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: sans-serif; max-width: 800px; margin: 2em auto; line-height: 1.6; }}
    a.timestamp {{ color: blue; text-decoration: underline; cursor: pointer; }}
    .player-row {{ display: flex; align-items: center; gap: 1em; }}
    audio {{ flex: 1; }}
    button.jump-button {{ padding: 0.5em 1em; font-size: 1em; }}
    .transcript-segment {{ scroll-margin-top: 6em; transition: background-color 0.3s ease; }}
    .highlight {{ background-color: yellow; }}
    .metadata {{
        color: #555;
        font-size: 0.9em;
        margin-top: -1em;
        margin-bottom: 2em;
        border-bottom: 1px solid #eee;
        padding-bottom: 1em;
    }}
    #scrollTopBtn {{
      position: fixed;
      top: 1em;
      right: 1em;
      display: none;
      display: flex;
      gap: 0.5em;
    }}
    #scrollTopBtn button {{
      padding: 0.5em 0.8em;
      background: #444;
      color: white;
      border: none;
      border-radius: 0.3em;
      cursor: pointer;
      font-size: 0.9em;
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 40px;
    }}
  </style>
</head>
<body>
  <h2>{title}</h2>
  {metadata_html}
  <div class="player-row">
    <audio id="player" controls preload="auto">
      <source src="{audio_data_uri}" type="audio/mpeg">
      Your browser does not support the audio element.
    </audio>
    <button class="jump-button" onclick="scrollToCurrentSegment()">To text</button>
  </div>
  <div id="transcript">
"""
    for i, (start, _, text) in enumerate(subtitles):
        html += f'<p id="seg{i}" class="transcript-segment"><a class="timestamp" onclick="seekTo({start:.2f})">[{format_timestamp(start)}]</a> {text}</p>\n'

    segment_array = [f"{{start: {start:.2f}, id: 'seg{i}'}}" for i, (start, _, _) in enumerate(subtitles)]
    segments_js = ",\n      ".join(segment_array)

    html += f"""
  </div>
  <div id="scrollTopBtn">
    <button onclick="scrollToTop()">↑ To audio</button>
    <button id="playPauseBtn" onclick="togglePlay()">▶</button>
  </div>
  <script>
    const player = document.getElementById("player");
    const playPauseBtn = document.getElementById("playPauseBtn");
    const segments = [
      {segments_js}
    ];

    function togglePlay() {{
      if (player.paused) {{
        player.play();
        scrollToCurrentSegment();
      }} else {{
        player.pause();
      }}
    }}

    player.addEventListener('play', () => {{
      playPauseBtn.textContent = '⏸';
    }});

    player.addEventListener('pause', () => {{
      playPauseBtn.textContent = '▶';
    }});

    function seekTo(seconds) {{
      const player = document.getElementById("player");
      player.currentTime = seconds;
      player.play();
    }}

    function scrollToCurrentSegment() {{
      const player = document.getElementById("player");
      const current = player.currentTime;
      let closest = segments[0];
      for (const s of segments) {{
        if (s.start <= current) {{
          closest = s;
        }} else {{
          break;
        }}
      }}
      const el = document.getElementById(closest.id);
      if (el) {{
        el.scrollIntoView({{ behavior: "smooth" }});
        el.classList.add("highlight");
        setTimeout(() => el.classList.remove("highlight"), 1000);
      }}
    }}

    function scrollToTop() {{
      window.scrollTo({{top: 0, behavior: 'smooth'}});
    }}

    window.addEventListener('scroll', () => {{
      const btnContainer = document.getElementById("scrollTopBtn");
      if (window.scrollY > 300) {{
        btnContainer.style.display = "flex";
      }} else {{
        btnContainer.style.display = "none";
      }}
    }});
  </script>
</body>
</html>
"""
    return html


def main():
    """Main function to run the script."""
    args = parse_args()

    if args.output is None:
        # Если путь не задан, используем имя аудиофайла с расширением .html
        output_path = Path(args.audio).with_suffix('.html')
    else:
        output_path = Path(args.output)

    assert os.path.exists(args.audio), f"Audio file not found: {args.audio}"
    assert os.path.exists(args.subtitles), f"Subtitle file not found: {args.subtitles}"

    audio_length = get_audio_duration(args.audio)
    subtitles = parse_srt(args.subtitles, audio_length)
    assert subtitles, "No valid subtitle entries found."

    title = os.path.basename(args.audio)
    metadata_parts = []
    try:
        audio_tags = ID3(args.audio)
        if 'TIT2' in audio_tags:
            title = str(audio_tags.get('TIT2').text[0])
        if 'COMM' in audio_tags:
            comment_text = audio_tags.getall('COMM')[0].text[0]
            metadata_parts.append(f"Comment: {comment_text}")
        if 'TLAN' in audio_tags:
            lang_text = str(audio_tags.get('TLAN').text[0])
            metadata_parts.append(f"Language: {lang_text}")
        if 'TDES' in audio_tags:
            podcast_info_text = str(audio_tags.get('TDES').text[0])
            metadata_parts.append(f"Podcast info: {podcast_info_text}")

    except ID3NoHeaderError:
        print("Info: No ID3 tags found in the audio file.")
    except Exception as e:
        print(f"Warning: Could not read ID3 tags. Error: {e}")

    metadata_str = ", ".join(metadata_parts)

    if args.no_embed_mp3:
        audio_data_uri = os.path.basename(args.audio)
    else:
        audio_data_uri = audio_to_base64(args.audio)

    html = render_html(audio_data_uri, subtitles, title, metadata_str)
    
    # Используем определённый ранее путь для сохранения файла
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML file successfully written to {output_path}")


if __name__ == "__main__":
    main()