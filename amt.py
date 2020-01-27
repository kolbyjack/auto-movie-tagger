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


def collect_files(file_type):
    return sorted([fn for fn in os.listdir(os.getcwd()) if fn.endswith(file_type)])

def readNfo(title):
    md = {}

    nfo_filename = "%s.nfo" % title
    if not os.path.isfile(nfo_filename):
        return md

    try:
        tree = ET.parse(nfo_filename)
        root = tree.getroot()
        for child in root:
            if child.tag in ("id", "title", "plot", "rating"):
                md[child.tag] = child.text
            elif child.tag == "capturedate":
                md["year"] = child.text
            elif child.tag == "genre":
                md.setdefault("genres", []).append(child.text)
    except:
        pass

    return md

def writeNfo(title, md):
    nfo_filename = "%s.nfo" % title
    if os.path.isfile(nfo_filename):
        return

    movie = ET.Element("movie")
    ET.SubElement(movie, "id").text = md["id"]
    ET.SubElement(movie, "rating").text = str(md["rating"])
    ET.SubElement(movie, "title").text = md["title"]
    ET.SubElement(movie, "plot").text = md["plot"]
    ET.SubElement(movie, "capturedate").text = str(md["year"])
    for genre in md["genres"]:
        ET.SubElement(movie, "genre").text = genre

    with open(nfo_filename, "wb") as fp:
        fp.write(ET.tostring(movie))

def fetchMetadata(title):
    metadata = readNfo(title)
    if "title" in metadata:
        return metadata

    imdb = Imdb()
    if "id" not in metadata:
        print("Searching IMDB")
        results = imdb.search_for_title(title)
        movie_results = [r for r in results if r["type"] == "feature" and r["year"] is not None]

        while len(movie_results) == 0:
            title = input("No results for \"%s\" Enter alternate/correct movie title >> " % title)

            results = imdb.search_for_title(title)
            movie_results = [r for r in results if r["type"] == "feature" and r["year"] is not None]

        exact_matches = [r for r in movie_results if r["title"].lower() == title.lower()]

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
                metadata["id"] = input("Enter IMDB id: ")
                movie_results = []
            else:
                movie_results = [movie_results[answer["index"]]]
        
        if len(movie_results) > 0:
            mpr = movie_results[0]
            metadata["id"] = mpr["imdb_id"]
            print("Fetching data for {} ({})".format(mpr["title"], mpr["year"]))
    else:
        print("Fetching data for %s" % metadata["id"])

    imdb_movie = imdb.get_title(metadata["id"])

    metadata["title"] = imdb_movie["base"]["title"]
    metadata["year"] = imdb_movie["base"]["year"]
    metadata["rating"] = imdb_movie["ratings"]["rating"]

    if "outline" in imdb_movie["plot"]:
        metadata["plot"] = imdb_movie["plot"]["outline"]["text"]
    else:
        metadata["plot"] = imdb_movie["plot"]["summaries"][0]["text"]

    metadata["genres"] = imdb.get_title_genres(metadata["id"])["genres"]

    writeNfo(title, metadata)

    return metadata

def fetchPoster(title, md):
    poster_filename = "%s.jpg" % title
    if os.path.isfile(poster_filename):
        return

    print("Fetching the movie poster...")
    tmdb_find = tmdb.Find(md["id"])
    tmdb_find.info(external_source="imdb_id")

    path = tmdb_find.movie_results[0]["poster_path"]
    complete_path = r"https://image.tmdb.org/t/p/w780" + path

    uo = urllib.request.urlopen(complete_path)
    with open(poster_filename, "wb") as poster_file:
        poster_file.write(uo.read())
        poster_file.close()

def start_process(filenames):
    for filename in filenames:
        try:
            title = filename[:-4]
            print("Processing %s" % title)
            md = fetchMetadata(title)
            writeNfo(title, md)
            fetchPoster(title, md)

            # TODO: link file to each genre subdir
        except Exception as e:
            print("\nERROR processing %s: %s\n" % (filename, e))
        print("")

os.chdir("/mnt/baikal/zerolatency")
start_process(collect_files(".mp4"))
