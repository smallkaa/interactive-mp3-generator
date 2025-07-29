# MP3 Transcript Generator

This Python script creates a single, self-contained HTML file from an MP3 audio file and a corresponding SRT subtitle file. The output provides an enhanced audio player with a synchronized, clickable transcript, making it easy to navigate and review audio content.

## Features

-   **Self-Contained & Portable**: Generates a single HTML file with the audio embedded (using base64), so it can be easily shared and opened anywhere.
-   **Interactive Transcript**: Each line of the transcript has a clickable timestamp that jumps the audio player to that exact moment.
-   **Dynamic Metadata**: Automatically uses the MP3's ID3 tags to set the page title and display metadata like comments, language, or podcast info. If no title tag is found, it defaults to the filename.
-   **Synchronized Scrolling**: A "To text" button instantly scrolls the page to the transcript segment that corresponds to the current audio playback time and highlights it.
-   **Convenient UI Controls**: Includes floating buttons to quickly scroll back to the player or toggle play/pause from anywhere on the page.
-   **Flexible Audio Linking**: An option (`--no-embed-mp3`) allows you to link to the audio file externally instead of embedding it, which is useful for large files.
-   **Smart File Naming**: By default, the output HTML file is named after the input MP3 file (e.g., `my-podcast.mp3` becomes `my-podcast.html`).

---

## Requirements

-   Python 3
-   The [mutagen](https://github.com/quodlibet/mutagen) library. You can install it via pip:
    ```bash
    pip install mutagen
    ```

---

## Usage

Run the script from your command line, providing the paths to your audio and subtitle files.

### Basic Command

```bash
python interactive_transcript.py --audio "path/to/your/audio.mp3" --subtitles "path/to/your/subs.srt" [--no-embed-mp3]
