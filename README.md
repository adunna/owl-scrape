# OWL-Scrape

This is a WIP for OWL Season 2 Stage 2.

It currently works with no known bugs. Please open an issue if you find any, or would like additional features. I maintain this in my spare time.

## Dependencies

 - Python 3
 - `pip3 install streamlink requests`
 - ffmpeg

## Setup

Install Python 3, the required Python 3 modules, and ffmpeg.

Clone the repository to your disk. Copy `config.sample.py` into `config.py`, and change `OAUTH_TOKEN` to your OAuth Token, obtained by using `streamlink --twitch-oauth-authenticate`.

Run the program with `python3 scrape.py` and profit!
