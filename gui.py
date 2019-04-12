from flask import Flask, jsonify, render_template, request
from threading import Thread
from multiprocessing import Process
import configparser
from scrape import OWLScraper
import time

class GUI():

    def __init__(self):
        self.MAIN = None
        self.CFG = configparser.ConfigParser()
        self.CFG.read("config.ini")
        self.SCRAPER = OWLScraper(self.CFG["MAIN"]["CLIENT_ID"], self.CFG["MAIN"]["OAUTH_TOKEN"], self.CFG["MAIN"]["QUALITY"])
        self.SCRAPER.CLI = False
        self.SCRAPER.Setup()
        
        self.MAPS = ",".join(list(set([self.SCRAPER.MAPS[x][0] for x in self.SCRAPER.MAPS if self.SCRAPER.MAPS[x][0] != "" and self.SCRAPER.MAPS[x][0] not in ["oasis-city-center","oasis-university","oasis-gardens"] and self.SCRAPER.MAPS[x][1] in ["assault","hybrid","control","escort"]])))
        self.ROLES = ",".join(self.SCRAPER.ROLES)
        self.TEAMS = ",".join([self.SCRAPER.TEAMS[x] for x in self.SCRAPER.TEAMS])
        self.PLAYERS = ",".join([x for x in self.SCRAPER.PLAYERS])

        if self.CFG["INCLUDE"]["maps"] == "all":
            self.CFG["INCLUDE"]["maps"] = self.MAPS
        if self.CFG["INCLUDE"]["roles"] == "all":
            self.CFG["INCLUDE"]["roles"] = self.ROLES
        if self.CFG["INCLUDE"]["teams"] == "all":
            self.CFG["INCLUDE"]["teams"] = self.TEAMS
        if self.CFG["INCLUDE"]["players"] == "all":
            self.CFG["INCLUDE"]["players"] = self.PLAYERS

        with open("config.ini", "w") as cf:
            self.CFG.write(cf)

        self.Setup()
        self.STOPSERVER = False
        self.MTHREAD = Thread(target=self.Run)
        self.MTHREAD.start()
        self.WPROC = Process(target=self.MAIN.run)
        self.WPROC.start()

    def Run(self):
        while not self.STOPSERVER:
            time.sleep(0.1)
        print("stop")
        self.MAIN.terminate()
        self.MAIN.join()

    def Setup(self):
        self.MAIN = Flask(__name__)
        self.MAIN.config.from_object(__name__)

        @self.MAIN.route('/stop')
        def stop():
            self.STOPSERVER = True
            return "Stopping server."

        @self.MAIN.route('/log')
        def log():
            def generate():
                if self.SCRAPER.OUTLOG != "":
                    return self.SCRAPER.OUTLOG
            return self.MAIN.response_class(generate(), mimetype='text/plain')

        @self.MAIN.route('/', methods=["POST", "GET"])
        def home():
            if request.method == "POST" and request.form["formtype"] == "config":
                if request.form["oauth-token"] is not None and len(request.form["oauth-token"]) >= 10:
                    self.CFG["MAIN"]["OAUTH_TOKEN"] = request.form["oauth-token"]
                if request.form["quality"] is not None and len(request.form["quality"]) >= 3:
                    self.CFG["MAIN"]["QUALITY"] = request.form["quality"]
                with open("config.ini", "w") as cf:
                    self.CFG.write(cf)
                self.SCRAPER.CLIENT_ID = self.CFG["MAIN"]["CLIENT_ID"]
                self.SCRAPER.OAUTH_TOKEN = self.CFG["MAIN"]["OAUTH_TOKEN"]
                self.SCRAPER.QUALITY = self.CFG["MAIN"]["QUALITY"]
                self.SCRAPER.CLI = False

            if request.method == "POST" and request.form["formtype"] == "scraper":
                if "start" in request.form and request.form["start"] == "Start":
                    self.SCRAPER.StartBG()
                elif "stop" in request.form and request.form["stop"] == "Stop":
                    self.SCRAPER.Stop()
                elif "save" in request.form and request.form["save"] == "Save Filters":
                    self.CFG["INCLUDE"]["maps"] = ",".join([x[2:] for x in request.form if x[0:2] == "m_"])
                    self.CFG["INCLUDE"]["roles"] = ",".join([x[2:] for x in request.form if x[0:2] == "r_"])
                    self.CFG["INCLUDE"]["teams"] = ",".join([x[2:] for x in request.form if x[0:2] == "t_"])
                    self.CFG["INCLUDE"]["players"] = ",".join([x[2:] for x in request.form if x[0:2] == "p_"])
                    with open("config.ini", "w") as cf:
                        self.CFG.write(cf)
                    self.SCRAPER.ReadFilters()

            conf = {"oauth": self.CFG["MAIN"]["OAUTH_TOKEN"], "quality": {}}
            conf["quality"]["one"] = "selected" if self.CFG["MAIN"]["QUALITY"] == "best" else ""
            conf["quality"]["two"] = "selected" if self.CFG["MAIN"]["QUALITY"] == "720p" else ""
            conf["quality"]["three"] = "selected" if self.CFG["MAIN"]["QUALITY"] == "480p" else ""
            conf["quality"]["four"] = "selected" if self.CFG["MAIN"]["QUALITY"] == "360p" else ""
            conf["quality"]["five"] = "selected" if self.CFG["MAIN"]["QUALITY"] == "audio_only" else ""

            maps = [(x, "checked" if x in self.CFG["INCLUDE"]["maps"].strip().split(",") else "") for x in sorted(self.MAPS.strip().split(","))]
            roles = [(x, "checked" if x in self.CFG["INCLUDE"]["roles"].strip().split(",") else "") for x in sorted(self.ROLES.strip().split(","))]
            teams = [(x, "checked" if x in self.CFG["INCLUDE"]["teams"].strip().split(",") else "") for x in sorted(self.TEAMS.strip().split(","))]
            players = [(x, "checked" if x in self.CFG["INCLUDE"]["players"].strip().split(",") else "") for x in sorted(self.PLAYERS.strip().split(","), key=lambda v: v.upper())]

            return render_template("index.html", conf=conf, maps=maps, roles=roles, teams=teams, players=players)
