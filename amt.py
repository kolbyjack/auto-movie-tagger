#!/usr/bin/env python

"""A Script that tags your movie files.

Run the script in a folder containing the mp4/mkv movie files with their
filename as the movie's title.

This script might seem a little messy and ugly and I know maybe there is
better and effecient way to do some of the tasks.
but I am unaware of them at the moment and am a begginer in Python and
this is my first, or maybe second python script.

"""
import os
import urllib
import sys
import types
import tmdbsimple as tmdb
from imdbpie import Imdb
import inquirer
import xml.etree.ElementTree as ET

#  Setting the API key for usage of TMDB API
tmdb.API_KEY = "b888b64c9155c26ade5659ea4dd60e64"

BASE_PATH = "/srv/media/movies"

class Video(object):
    def __init__(self, filepath):
        self._dir, self._filename = os.path.split(filepath)
        self._title, self._ext = os.path.splitext(self._filename)
        self._md = {}

    def _build_filepath(self, ext):
        filename = "{}.{}".format(self._title, ext)
        return os.path.join(self._dir, filename)

    def _read_nfo(self):
        nfo_filename = self._build_filepath("nfo")
        if not os.path.isfile(nfo_filename):
            return

        tree = ET.parse(nfo_filename)
        root = tree.getroot()
        for child in root:
            if child.tag in ("id", "title", "plot"):
                self._md[child.tag] = child.text
            elif child.tag == "capturedate":
                self._md["year"] = child.text
            elif child.tag == "genre":
                self._md.setdefault("genres", []).append(child.text)

    def _write_nfo(self):
        nfo_filename = self._build_filepath("nfo")

        movie = ET.Element("movie")
        ET.SubElement(movie, "id").text = self._md["id"]
        ET.SubElement(movie, "title").text = self._md["title"]
        ET.SubElement(movie, "plot").text = self._md["plot"]
        ET.SubElement(movie, "capturedate").text = str(self._md["year"])
        for genre in self._md["genres"]:
            ET.SubElement(movie, "genre").text = genre

        with open(nfo_filename, "wb") as fp:
            fp.write(ET.tostring(movie))

    def _fetch_metadata(self):
        searchtitle = self._title
        if searchtitle.endswith(", The"):
            searchtitle = "The {}".format(searchtitle[:-5])
        elif searchtitle.endswith(", A"):
            searchtitle = "A {}".format(searchtitle[:-3])

        imdb = Imdb()
        if "id" not in self._md:
            print("  * Searching IMDB")
            results = imdb.search_for_title(searchtitle)
            movie_results = [r for r in results if r["type"] == "feature" and r["year"] is not None]

            while len(movie_results) == 0:
                searchtitle = input("No results for \"%s\" Enter alternate/correct movie title >> " % searchtitle)

                results = imdb.search_for_title(searchtitle)
                movie_results = [r for r in results if r["type"] == "feature" and r["year"] is not None]

            exact_matches = [r for r in movie_results if r["title"].lower() == searchtitle.lower()]

            if len(exact_matches) > 0:
                movie_results = exact_matches

            if len(movie_results) > 1:
                choices=[("%s (%s)" % (r["title"], r["year"]), idx) for idx, r in enumerate(movie_results)]
                choices.append(("Not found", -1))
                answer = inquirer.prompt([
                    inquirer.List("index",
                        message="Multiple results found:",
                        choices=choices
                    )
                ])
                if answer["index"] == -1:
                    self._md["id"] = input("Enter IMDB id: ")
                    movie_results = []
                else:
                    movie_results = [movie_results[answer["index"]]]

            if len(movie_results) > 0:
                mpr = movie_results[0]
                self._md["id"] = mpr["imdb_id"]
                print("  * Fetching data for {} ({})".format(mpr["title"], mpr["year"]))
        else:
            print("  * Fetching data for %s" % self._md["id"])

        imdb_movie = imdb.get_title(self._md["id"])

        self._md["title"] = imdb_movie["base"]["title"]
        self._md["year"] = imdb_movie["base"]["year"]

        if "outline" in imdb_movie["plot"]:
            self._md["plot"] = imdb_movie["plot"]["outline"]["text"]
        else:
            self._md["plot"] = imdb_movie["plot"]["summaries"][0]["text"]

        self._md["genres"] = imdb.get_title_genres(self._md["id"])["genres"]

        self._write_nfo()

    def _fetch_poster(self):
        poster_filename = self._build_filepath("jpg")
        if os.path.isfile(poster_filename):
            return

        print("  * Fetching the movie poster")
        tmdb_find = tmdb.Find(self._md["id"])
        tmdb_find.info(external_source="imdb_id")

        if len(tmdb_find.movie_results) == 0:
            print("    * Unable to find movie poster for {}".format(self._md["id"]))
            return

        poster_url = r"https://image.tmdb.org/t/p/w780{}".format(tmdb_find.movie_results[0]["poster_path"])

        uo = urllib.request.urlopen(poster_url)
        with open(poster_filename, "wb") as poster_file:
            poster_file.write(uo.read())
            poster_file.close()

    def _dirty(self):
        if not os.path.exists(self._build_filepath("jpg")):
            return True

        self._read_nfo()
        if "title" not in self._md:
            return True

        return False

    def process(self):
        try:
            print("Processing {}".format(self._title), end="\r")
            if not self._dirty():
                return

            print("")
            self._read_nfo()
            self._fetch_metadata()
            self._write_nfo()
            self._fetch_poster()
        except Exception as e:
            print("  *** ERROR processing {}: {}".format(filename, e))

allMovies = sorted([os.path.join(BASE_PATH, fn) for fn in os.listdir(BASE_PATH) if fn.endswith(".mp4")])
for filename in allMovies:
    Video(filename).process()
    print(" " * len("Processing {}".format(filename)), end="\r")
