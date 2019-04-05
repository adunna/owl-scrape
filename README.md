# OWL-Scrape

Automagically download all 14 live OWL streams (6 player POVs from both sides, map VOD, and spectator VOD) to disk for later viewing. Categorizes them for you.

---

This is a WIP for OWL Season 2 Stage 2.

It currently works with no known bugs. Please open an issue if you find any, or would like additional features. I maintain this in my spare time.

## Dependencies

 - (Currently) Linux only
 - Python 3
 - `pip3 install streamlink requests`
 - `ffmpeg`

## Setup

Install Python 3, the required Python 3 modules, and ffmpeg.

Clone the repository to your disk. Copy `config.sample.py` into `config.py`, and change `OAUTH_TOKEN` to your OAuth Token, obtained by using `streamlink --twitch-oauth-authenticate`.

Set `QUALITY` in `config.py` to your preferred quality, if it is not best (1080p60) by default. Note this is 14 separate streams at whatever quality you set, so have your bandwidth ready.

Quality options are: `"audio_only"`, `"360p"`, `"480p"`, `"720p"`, and `"best"`, where best = 1080p60.

Run the program with `python3 scrape.py` and profit!
