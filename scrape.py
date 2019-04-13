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
import configparser
from sys import platform

class OWLScraper():

    def __init__(self, cid="", otoken="", qual=""):

        self.GAME_STATES = {"curr": "IN_PROGRESS", "future": "PENDING", "fin": "CONCLUDED"}
        
        self.CLIENT_ID = cid
        self.OAUTH_TOKEN = otoken
        self.QUALITY = qual
        self.OUT_DIR = "matches"
        self.MOVE_DIR = None
        self.PROCESS_STREAMS = True

        self.CLI = True
        self.WEBC = ""

        self.MATCHES = []
        self.GAMES = []
        
        self.PREV_MAP_ID = -1
        self.CURRENT_MATCH = []
        self.STREAMS = []
        self.STREAM_FILES = []
        self.LOGGED_MON = False
        self.RUNNING = False
        self.RECORDING = False
        self.MAIN_THREAD = None
        self.PROCESS_THREAD = None
        self.STOP_PROCESSING = False
        self.OUTLOG = ""

        self.MAPS = {}
        self.TEAMS = {}
        self.PLAYERS = {}
        self.ROLES = []
        self.MODES = []

        self.MAP_FILTER = []
        self.TEAM_FILTER = []
        self.PLAYER_FILTER = []
        self.ROLE_FILTER = []

    # Run initial setup of OWL Scraper
    def Setup(self):
        self.MAPS, self.TEAMS, self.PLAYERS, self.ROLES, self.MODES = self.GetLatestInfo()
        self.ReadFilters()

    # Update filters from configuration file
    def ReadFilters(self):
        cfg = configparser.ConfigParser()
        cfg.read("config.ini")
        self.MAP_FILTER = cfg["INCLUDE"]["maps"].strip().split(",")
        self.TEAM_FILTER = cfg["INCLUDE"]["teams"].strip().split(",")
        self.PLAYER_FILTER = cfg["INCLUDE"]["players"].strip().split(",")
        self.ROLE_FILTER = cfg["INCLUDE"]["roles"].strip().split(",")

    # Stops OWL Scraper
    def Stop(self):
        self.Log("Stopping scraper. Please allow up to 1 minute to stop.")
        self.RUNNING = False
        if self.RECORDING:
            self.RECORDING = False
            self.StopRecord()
        if self.PROCESS_THREAD is not None:
            self.STOP_PROCESSING = True

    # Deploy OWL Scraper in background
    def StartBG(self):
        x = Thread(target=self.Start)
        x.start()

    # Deploy OWL Scraper
    def Start(self):
        if self.CLI == False:
            self.WEBC = "s"
        while True:
            if self.CLI == True:
                userInput = input()
            else:
                while self.WEBC == "":
                    time.sleep(1)
                userInput = self.WEBC
                self.WEBC = ""
            if userInput is not None:
                if userInput.lower() == "s" and self.MAIN_THREAD is None:
                    self.Setup()
                    self.STOP_PROCESSING = False
                    self.MAIN_THREAD = Thread(target=self.StartScraper)
                    self.MAIN_THREAD.start()
                elif userInput.lower() == "q":
                    self.Stop()
                    self.MAIN_THREAD = None
                    self.PROCESS_THREAD = None
                elif userInput.lower() == "e":
                    self.Stop()
                    self.MAIN_THREAD = None
                    self.PROCESS_THREAD = None
                    break
            if self.CLI:
                self.Log("Options are S to Start, Q to Stop, E to Exit.")
        self.Log("Exiting scraper. Happy viewing!")

    # Starts OWL Scraper in loop
    def StartScraper(self):

        if self.CLI:
            self.Log("Starting scraper. Enter Q to stop scraping.")
        else:
            self.Log("Starting scraper.")

        self.RUNNING = True
        try:
            while self.RUNNING:

                # Get latest OWL schedule and current game if any
                #self.MATCHES, self.GAMES = self.GetOWLSchedule()
                self.MATCHES, self.GAMES = self.GetLiveMatch()
                self.CURRENT_MATCH = self.GetCurrentMatch()

                # Found current game
                if self.CURRENT_MATCH != [] and len(self.CURRENT_MATCH) >= 4:
                    if self.CURRENT_MATCH[1] != self.PREV_MAP_ID and self.CURRENT_MATCH[4] in self.MAP_FILTER and self.TEAMS[self.CURRENT_MATCH[2]] in self.TEAM_FILTER and self.TEAMS[self.CURRENT_MATCH[3]] in self.TEAM_FILTER:
                        self.PREV_MAP_ID = self.CURRENT_MATCH[1]
                        self.Log("Recording game: #%s - %s vs. %s - Map %s" % (self.CURRENT_MATCH[0], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3], self.CURRENT_MATCH[4]))

                        # Already recording, but map changed
                        # Or not already recording

                        if self.RECORDING:
                            self.StopRecord()
                            self.ProcessStreams()
                            self.MakeDirectories()
                            self.StartRecord()
                            self.LOGGED_MON = False
                        else:
                            self.MakeDirectories()
                            self.StartRecord()

                        self.RECORDING = True

                else:

                    # Not currently running, stop record if finished
                    if not self.LOGGED_MON:
                        self.LOGGED_MON = True
                        self.Log("No game currently detected. Monitoring...")
                    if self.RECORDING:
                        self.Log("Game finished, stopped recording. Running conversion in background.")
                        self.LOGGED_MON = False
                        self.RECORDING = False
                        self.StopRecord()
                        self.ProcessStreams()
                        self.Setup()

                time.sleep(30)

        except Exception as e:
            self.RUNNING = False
            self.RECORDING = False
            self.STOP_PROCESSING = True
            self.StopRecord()
            self.Log("Encountered error: " + str(e))
            self.Log("Stopping and exiting program.")

    # Output to log, i.e. print to CLI or output to web
    def Log(self, outstr):
        if self.CLI:
            print("[ %s ]  %s" % (datetime.datetime.now().strftime("%H:%M:%S"), outstr))
        else:
            self.OUTLOG = ("[ %s ]  %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), outstr)) + self.OUTLOG

    # Start sub stream output with streamlink
    def SubStream(self, chan_name, file_name):
        # OUTDIR/map/date/team1_team2/type.flv
        outFile = "%s/%s/%s/%s_%s/%s.flv" % (self.OUT_DIR, self.CURRENT_MATCH[4], self.CURRENT_MATCH[5], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3], file_name)
        self.STREAM_FILES.append(outFile)
        if platform == "linux" or platform == "linux2" or platform == "darwin":
            self.STREAMS.append(subprocess.Popen("exec streamlink --twitch-oauth-token %s twitch.tv/%s %s -o %s" % (self.OAUTH_TOKEN, chan_name, self.QUALITY, outFile), stdout=subprocess.PIPE, shell=True))
        else:
            self.STREAMS.append(subprocess.Popen("streamlink --twitch-oauth-token %s twitch.tv/%s %s -o %s" % (self.OAUTH_TOKEN, chan_name, self.QUALITY, outFile), stdout=subprocess.PIPE, shell=True))

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
                    if player in self.PLAYER_FILTER and self.PLAYERS[player][0] in self.ROLE_FILTER:
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

    # Process files after streams have ended
    def ProcessStreams(self):
        self.PROCESS_THREAD = Thread(target=self.RunProcessStreams)
        self.PROCESS_THREAD.start()

    def RunProcessStreams(self):
        copyStreams = self.STREAM_FILES
        self.STREAM_FILES = []
        time.sleep(30)
        if self.PROCESS_STREAMS:
            for streamFile in copyStreams:
                try:
                    P = subprocess.Popen("ffmpeg -i %s -c:v libx264 -crf 22 -preset slow -c:a mp3 %s >/dev/null 2>&1" % (streamFile, streamFile[:-3] + "mp4"), stdout=subprocess.PIPE, shell=True)
                    while self.STOP_PROCESSING == False and P.poll() == None:
                        time.sleep(0.1)
                    if self.STOP_PROCESSING:
                        P.kill()
                        return
                    os.remove(streamFile)
                except:
                    pass

    # Make directories for streams
    def MakeDirectories(self):
        # OUTDIR/map/date/team1_team2/type.flv
        if not os.path.exists(self.OUT_DIR):
            os.makedirs(self.OUT_DIR)
        for mapx in [self.CURRENT_MATCH[4]]:
            if not os.path.exists("%s/%s" % (self.OUT_DIR, mapx)):
                os.mkdir("%s/%s" % (self.OUT_DIR, mapx))
            if not os.path.exists("%s/%s/%s" % (self.OUT_DIR, mapx, self.CURRENT_MATCH[5])):
                os.mkdir("%s/%s/%s" % (self.OUT_DIR, mapx, self.CURRENT_MATCH[5]))
            if not os.path.exists("%s/%s/%s/%s_%s" % (self.OUT_DIR, mapx, self.CURRENT_MATCH[5], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3])):
                os.mkdir("%s/%s/%s/%s_%s" % (self.OUT_DIR, mapx, self.CURRENT_MATCH[5], self.CURRENT_MATCH[2], self.CURRENT_MATCH[3]))

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

    # Fetch the latest current match, returning [match], [games]
    def GetLiveMatch(self):
        response = requests.get("https://api.overwatchleague.com/live-match")
        response = response.json()
        matches = [response["data"]["liveMatch"]]
        games = response["data"]["liveMatch"]["games"]
        return (matches, games)

    # Fetch the latest maps, teams, players, roles, and modes, returning {mapguid: (name, mode) ...}, {abbrev: team, ..}, {player: (role, teamabbrev), ...}, [roles], [modes]
    def GetLatestInfo(self):
        try:
            response = requests.get("https://api.overwatchleague.com/teams").json()
            teams = {team["competitor"]["abbreviatedName"]: team["competitor"]["name"] for team in response["competitors"]}
            players = {player["player"]["name"]: (player["player"]["attributes"]["role"], team["competitor"]["abbreviatedName"]) for team in response["competitors"] for player in team["competitor"]["players"]}
            response = requests.get("https://api.overwatchleague.com/maps").json()
            maps = {mapx["guid"]: (mapx["id"], mapx["type"]) for mapx in response if mapx["id"] != ""}
            roles = list(set([players[player][0] for player in players]))
            modes = [x for x in set([maps[mapx][1] for mapx in maps])]
            return (maps, teams, players, roles, modes)
        except:
            return (self.MAPS, self.TEAMS, self.PLAYERS, self.ROLES, self.MODES)
        
    # If match is currently going, return [int matchnum, int mapnum, str team1, str team2, str map, str date, str mode]
    # Otherwise, returns empty arr
    def GetCurrentMatch(self):
        try:
            running = [game for game in self.GAMES if game['state'] == self.GAME_STATES["curr"]]
            if len(running) == 0:
                return []
            match = [m for m in self.MATCHES if m['id'] == running[0]['match']['id']][0]
            return [match['id'], running[0]['number'], match['competitors'][0]['abbreviatedName'], match['competitors'][1]['abbreviatedName'], self.MAPS[running[0]['attributes']['mapGuid']][0], datetime.datetime.now().strftime("%Y-%m-%d"), self.MAPS[running[0]['attributes']['mapGuid']][1]]
        except Exception as e:
            self.Log("Encountered error: " + str(e))
            return []

