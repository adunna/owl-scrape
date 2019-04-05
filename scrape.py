import config
import datetime
import http.client
from urllib.parse import quote, urlencode
from urllib.request import *
import urllib
import requests
import streamlink
import json
import time
import subprocess
import os
import signal
from itertools import chain
from threading import Thread

class OWLScraper():

    def __init__(self):
        self.GAME_STATES = {"curr": "IN_PROGRESS", "future": "PENDING", "fin": "CONCLUDED"}
        self.CLIENT_ID = config.CLIENT_ID
        self.OAUTH_TOKEN = config.OAUTH_TOKEN
        self.QUALITY = config.QUALITY
        self.MATCHES = []
        self.GAMES = []
        self.PREV_MATCH_ID = 0
        self.CURRENT_MATCH = []
        self.STREAMS = []
        self.RUNNING = False
        self.RECORDING = False
        self.MAIN_THREAD = None

    # Stops OWL Scraper
    def Stop(self):
        self.Log("Stopping scraper. Please allow up to 1 minute to stop.")
        self.RUNNING = False
        if self.RECORDING:
            self.RECORDING = False
            self.StopRecord()

    # Deploy OWL Scraper
    def Start(self):
        while True:
            userInput = input()
            if userInput is not None:
                if userInput.lower() == "s" and self.MAIN_THREAD is None:
                    self.MAIN_THREAD = Thread(target=self.StartScraper)
                    self.MAIN_THREAD.start()
                elif userInput.lower() == "q":
                    self.Stop()
                    self.MAIN_THREAD = None
                elif userInput.lower() == "e":
                    self.Stop()
                    self.MAIN_THREAD = None
                    break
            self.Log("Options are S to Start, Q to Stop, E to Exit.")
        self.Log("Exiting scraper. Happy viewing!")


    # Starts OWL Scraper in loop
    def StartScraper(self):
        
        self.Log("Starting scraper. Press Q to stop scraping.")

        self.RUNNING = True
        try:
            while self.RUNNING:
            
                # Get latest OWL schedule and current game if any
                self.MATCHES, self.GAMES = self.GetOWLSchedule()
                self.CURRENT_MATCH = self.GetCurrentMatch()

                # Found current game
                if self.CURRENT_MATCH != []:
                    if self.CURRENT_MATCH[0] != self.PREV_MATCH_ID:
                        self.PREV_MATCH_ID = self.CURRENT_MATCH[0]
                        self.RECORDING = True
                        self.Log("Recording game: #%s - %s vs. %s - Map %s" % (self.CURRENT_MATCH[0], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3], self.CURRENT_MATCH[1]))

                        # Already recording, but map changed
                        # Or not already recording

                        if self.RECORDING:
                            self.StopRecord()
                            self.MakeDirectories()
                            self.StartRecord()
                        else:
                            self.MakeDirectories()
                            self.StartRecord()

                else:

                    # Not currently running, stop record if finished
                    self.Log("No game currently detected.")
                    if self.RECORDING:
                        self.RECORDING = False
                        self.StopRecord()

                time.sleep(30)

        except Exception as e:
            self.RUNNING = False
            self.RECORDING = False
            self.StopRecord()
            self.Log("Encountered error: " + str(e))
            self.Log("Stopping and exiting program.")

    # Output to log (currently prints)
    def Log(self, outstr):
        print("[ %s ]  %s" % (datetime.datetime.now().strftime("%H:%M:%S"), outstr))

    # Start sub stream output with streamlink
    def SubStream(self, chan_name, file_name):
        self.STREAMS.append(subprocess.Popen("exec streamlink --twitch-oauth-token %s twitch.tv/%s %s -o matches/%s/%s_%s_vs_%s/map%s_%s.flv" % (self.OAUTH_TOKEN, chan_name, self.QUALITY, self.CURRENT_MATCH[5], self.CURRENT_MATCH[0], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3], self.CURRENT_MATCH[1], file_name), stdout=subprocess.PIPE, shell=True))

    # Start record process
    def StartRecord(self):

        success = False
        
        # Run until success (in case of error starting too soon with API)
        while not success:
            channel_info = self.GetChannelInfo()
            if channel_info is not None:
                if "main" in channel_info:
                    self.SubStream(channel_info["main"], "main")
                if "map" in channel_info:
                    self.SubStream(channel_info["map"], "map")
                for player in channel_info["pov"]:
                    self.SubStream(channel_info["pov"][player], "%s_%s" % ("POV", player))
                success = True

    # Stop record process
    def StopRecord(self):
        for proc in self.STREAMS:
            try:
                proc.kill()
            except:
                pass
        self.STREAMS = []

    # Make directories for streams
    def MakeDirectories(self):
        if not os.path.exists("matches"):
            os.mkdir("matches")
        if not os.path.exists("matches/%s" % (self.CURRENT_MATCH[5],)):
            os.mkdir("matches/%s" % (self.CURRENT_MATCH[5],))
        if not os.path.exists("matches/%s/%s_%s_vs_%s" % (self.CURRENT_MATCH[5], self.CURRENT_MATCH[0], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3])):
            os.mkdir("matches/%s/%s_%s_vs_%s" % (self.CURRENT_MATCH[5], self.CURRENT_MATCH[0], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3]))

    # Gets information for channels (POV, etc.)
    def GetChannelInfo(self):
        try:
            conn = http.client.HTTPSConnection("gql.twitch.tv")
            postData = [{"operationName":"MultiviewGetChanletDetails","variables":{"channelLogin":"overwatchleague"},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"23e36d2b3a68dcb2f634dd5d7682e3a918a5598f63ad3a6415a6df602e3f7447"}}}]
            postHeaders = {'Content-Type': 'text/plain;charset=UTF-8', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36', 'Referer': 'https://www.twitch.tv/overwatchleague/commandcenter', 'Client-Id': self.CLIENT_ID}
            conn.request("POST", '/gql', json.dumps(postData), headers=postHeaders)
            response = conn.getresponse()
            info = None
            if response is not None and response.status == 200:
                info = json.loads(response.read().decode('utf-8'))
            conn.close()
            if info is not None:
                streamInfo = {"pov": {}}
                for chanlet in info[0]['data']['user']['channel']['chanlets']:
                    channel = chanlet['owner']['login']
                    infoArr = []
                    for attribute in chanlet['contentAttributes']:
                        if attribute['key'] == 'displayTitle':
                            infoArr = [x.strip() for x in attribute['value'].split("/")]
                    if len(infoArr) == 1 and "Main" in infoArr[0]:
                        streamInfo["main"] = channel
                    elif len(infoArr) == 1 and "Map" in infoArr[0]:
                        streamInfo["map"] = channel
                    elif len(infoArr) == 2 and infoArr[1] == "POV":
                        streamInfo["pov"][infoArr[0]] = channel

                return streamInfo
            return None

        except Exception as e:
            print(e)
            return None

    # Fetch latest OWL schedule and return [matches], [games]
    def GetOWLSchedule(self):
        response = requests.get("https://api.overwatchleague.com/schedule")
        response = response.json()
        matches = list(chain.from_iterable([stage["matches"] for stage in response["data"]["stages"]]))
        games = list(chain.from_iterable([match["games"] for match in matches]))
        return (matches, games)

    # If match is currently going, return [int matchnum, int mapnum, str team1, str team2, str map, str date]
    # Otherwise, returns empty arr
    def GetCurrentMatch(self):
        try:
            running = [game for game in self.GAMES if game['state'] == self.GAME_STATES["curr"]]
            if len(running) == 0:
                return []
            match = [m for m in self.MATCHES if m['id'] == running[0]['match']['id']][0]
            return [match['id'], running[0]['number'], match['competitors'][0]['abbreviatedName'], match['competitors'][1]['abbreviatedName'], "to_be_implemented", datetime.datetime.now().strftime("%Y-%m-%d")]
        except Exception as e:
            self.Log("Encountered error: " + str(e))
            return []

OWSC = OWLScraper()
OWSC.Log("OWL Scraper loaded. Press S to start scraping. Press E to exit.")
OWSC.Start()
