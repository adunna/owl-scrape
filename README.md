![](static/version1-1.png)

# OWL-Scrape

Automagically download all 14 live OWL streams (6 player POVs from both sides, map VOD, and spectator VOD) to disk for later viewing. Categorizes them for you.

Has a nice GUI. Working on distributing binaries. :)

---

This is a WIP for OWL Season 2 Stage 2.

It currently works with no known bugs. Please open an issue if you find any, or would like additional features. I maintain this in my spare time.

## Dependencies

 - Should run on other OSes, but only tested on Linux
 - Python 3
 - `pip3 install streamlink requests flask`
 - `ffmpeg`

## Setup / Usage

Install Python 3, the required Python 3 modules, and ffmpeg.

Clone the repository to your disk.

Execute the main program with `python3 main.py` and navigate to `http://localhost:5000` in your browser.

Obtain your Twitch OAuth token via the button on the web panel, and enter it into the text box, and choose your preferred quality then click the "Save Changes" button.

Apply your wanted filters, then click "Save Filters" to save the filters.

Click the "Start" button or "Stop" button to start the scraper or stop it, respectively.

Note that you do not have to restart the scraper to activate new filters or stream quality, it will be applied to the next seen game. You also are able to close the web panel at any time and as long as the Python program is running, it will continue to scrape in the background.
