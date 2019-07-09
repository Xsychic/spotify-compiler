# SPOTIFY TOP 100 PLAYLIST COMPILER

# WEB SCRAPER

import re
import csv
import sys
import os.path
import spotipy
import datetime
import requests
import spotipy.util as util
from bs4 import BeautifulSoup


#key global variables
username = 'xsychic'
today = datetime.datetime.today() #get todays datetime object
filename = './latest_playlist_100.csv' #last top 100 chart in csv
playlist_id = '2BACMBa5yXg0zsQtI5Wq8B' #top 100 playlist id
client_id = '1b7c94f5677445369a1d0201f2d306d6'
client_secret = '31e9685d49f14754a6f979c534ddea38'
url = 'https://www.officialcharts.com/charts/singles-chart/' #top 100 url

#get date in readable format
date = datetime.date.today().strftime("{}/{}/{}".format("%d", "%m", "%y"))

#get date and time in integer format
weekday = today.weekday()
now = datetime.datetime.now()
midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
seconds = (now - midnight).seconds
cutoff_time = 64800 #18:00pm in seconds

#select correct url based on date and time
if weekday > 4 or weekday == 4 and seconds >= cutoff_time:
    #top 100 chart url
    url = 'https://www.officialcharts.com/charts/singles-chart/'
else:
    #top 100 chart update url
    url = 'https://www.officialcharts.com/charts/singles-chart-update/'

def scrape_table(url):
    #go to url above and get data from table
    response = requests.get(url)
    html = response.content

    #get table
    soup = BeautifulSoup(html, features="html.parser")
    table = soup.find("table", attrs={"class": "chart-positions"})

    # create songs list
    songs = []

    for row in table.findAll("tr"):
        # find current position in songs list and add new object
        if "<span class=\"position\">" in str(row) and "<div class=\"track\">" in str(row):
            index = len(songs)
            songs.append([])

            for cell in row.findAll("td"):
                if "<span class=\"position\">" in str(cell):
                    # add song position to song list
                    pos_span = str(cell.find("span", attrs={"class": "position"}))
                    songs[index].append(pos_span[pos_span.index(">")+1:pos_span.index("</span>")].replace("&amp;", "&"))

                if "<div class=\"track\">" in str(cell):
                    # add song artist to song list
                    art_div = cell.find("div", attrs={"class": "artist"})
                    art_link = str(art_div.find("a"))
                    songs[index].append(art_link[art_link.index(">")+1:art_link.index("</a>")].replace("&amp;", "&"))

                    # add song title to song list
                    tit_div = cell.find("div", attrs={"class": "title"})
                    tit_link = str(tit_div.find("a"))
                    songs[index].append(tit_link[tit_link.index(">")+1:tit_link.index("</a>")].replace("&amp;", "&"))

    return songs


def read_old_songs():
    #read in scraped top 100 csv
    
    old_songs = []

    if os.path.exists(filename):
        with open(filename, "r", newline='') as infile:
            #readlines
            reader = csv.reader(infile, delimiter=',', quotechar='"')

            #append songs to list
            for row in reader:
                old_songs.append(row)

            #save compile date
            date = old_songs[0][3]

            #remove field titles
            old_songs.pop(0)

    return old_songs


def count_changes(songs, old_songs):
    #count how many songs have changed position
    changes = 0

    #check if old record exists
    if len(old_songs) > 0:
        #get each new and old song in order
        for index,song in enumerate(songs):

            #check if element in both lists exists
            if song and old_songs[index]:
                #check if new and old songs have moved
                if song != old_songs[index]:
                    changes += 1
    else:
        return len(songs)

    #return number of changes
    return changes


def count_new_entries(songs, old_songs):
    #count how many new entries in the chart
    new_entries = 0
    #get only title and artist from each song, omit position
    old_song_tracks = [[old_song[1], old_song[2]] for old_song in old_songs]

    #go through all new songs in order
    for song in songs:
        #check if song was in the last chart
        if [song[1], song[2]] not in old_song_tracks:
            new_entries += 1

    return new_entries


def record_table(songs):
# write table to csv

    try:
        #open file
        with open(filename, mode="w", newline='') as outfile:
            writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            #write header and songs
            writer.writerow(['Position','Artist','Track', date])
            writer.writerows(songs)

        print("\nData has been parsed.\n")

    except:
        #catch error often caused by file being open
        print("\nError. This may be because a version of the file being generated is currently open.")


def get_token():
    #api authentication
    
    token = util.prompt_for_user_token(username, scope='playlist-modify-private,playlist-modify-public', client_id=client_id, client_secret=client_secret, redirect_uri='https://localhost:8080')

    if token:
        #if a token is returned
        spotify = spotipy.Spotify(auth=token)
    else:
        print("That didn't work, try again?")

    return [spotify,token]

    
def get_song_ids(songs):
    #get uri for each song in top 100

    uris = []

    for song in songs:
        #strip to first artist only
        song[1] = song[1].split('&')[0]
        song[1] = song[1].split(' FT ')[0]
        song[1] = song[1].split('/')[0]
        
        
        #search for song using api

        try:
            #search by artist and song
            results = spotify.search(q='{} {}'.format(song[1], song[2]), type='track', limit='1')
            song_obj = results['tracks']['items'][0]
        except:
            try:
                #search by song
                results = spotify.search(q='{}'.format(song[2]), type='track', limit='1')
                song_obj = results['tracks']['items'][0]
            except:
                print("Could not find the number {} song {} by {}".format(song[0], song[2], song[1]))

                
        if song_obj:
            #if song returned, store its uri
            uris.append(song_obj['uri'])

            print("Added {} songs to the playlist".format(song[0]))
        else:
            #else return error
            print("Couldn't find a result for {} by {}.".format(song[2], song[1]))

    return uris


def send_tracks_to_playlist(uris):
    #add tracks to playlist by uri
    
    results = spotify.user_playlist_replace_tracks(username, playlist_id, uris)
    spotify.user_playlist_change_details(username, playlist_id, name='{} UK Top 100'.format(date))

    print("\nPlaylist of the UK top 100 from {} compiled".format(date))
    print("There have been {} changes and {} new entries in the chart.".format(changes, new_entries))



#call control functions
songs = scrape_table(url)
auth = get_token()

#returned auth values
spotify = auth[0]
token = auth[1]

#read in last chart
old_songs = read_old_songs()

#count changes and new entries
changes = count_changes(songs, old_songs)
new_entries = count_new_entries(songs, old_songs)

#write new chart to csv
record_table(songs)

#use songs array to compile uris
uris = get_song_ids(songs)
send_tracks_to_playlist(uris)




