import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime
import math
import random
import os


current_hour = 10 #int(datetime.now().hour)
current_day = "Saturday" #datetime.now().strftime("%A")


if os.path.exists('.cache'):
    os.remove('.cache')

#Spotify application credentials
credentials_dicts = [
    {
        'client_id':'42342781a4a24920ad9e2bdc6fadf7d8',
        'client_secret':'7cd3cea1117c44949230e0c5eae6f749',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'b348fdbb04354b4d97043b3a5ccaf9bd',
        'client_secret':'21c57025090542c69fc29b25a3ca2cf3',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'39c7d018efbc44e2ba4c415b287b1869',
        'client_secret':'80f021fbbc4043e394e41bb643f288bf',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'9cb9359fbbf54c40b3208420ceedfae2',
        'client_secret':'fee1e4637dac446880a2594225fd36f5',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'2a27a902ccdc45cda1b07c80d3b76028',
        'client_secret':'fbb746585a844fdd9108c2d37512bc68',
        'redirect_uri':'https://www.google.com'
    }
]

random_credentials = random.choice(credentials_dicts)


#interact with the spotify API
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**random_credentials, scope="playlist-modify-private user-read-recently-played"))


def compute_recently_played_songs():
    #try to load the accumulated listening history (spotify API only allows to retrieve the last 50 songs of the listening history)
    try:
        with open("data/recently_played_songs.bin", "rb") as file:
            recently_played_songs = pickle.load(file)
    except FileNotFoundError:
        recently_played_songs = {'items': []}

    existing_song_keys = {(item['track']['id'], item['played_at']) for item in recently_played_songs['items']}

    #get the last 50 songs in the listening history and keep only the ones that have not been stored yet
    new_songs = [song for song in spotify.current_user_recently_played()['items'] if (song['track']['id'], song['played_at']) not in existing_song_keys]

    #add to the existing songs in the playlist the new ones
    recently_played_songs['items'].extend(new_songs)


    with open("data/recently_played_songs.bin", "wb") as file:
        pickle.dump(recently_played_songs, file)

    #order the listening history by decreasing playing timestamp
    recently_played_songs = sorted(recently_played_songs['items'], key=lambda x: x['played_at'], reverse=True)

    #remove consecutive duplicates and songs that have been played for too little time
    unique_songs = [recently_played_songs[0]] 
    for i in range(1, len(recently_played_songs)):
        current_song = recently_played_songs[i]
        previous_song = recently_played_songs[i - 1]

        #Compute the difference of the two timestamps
        current_time = datetime.fromisoformat(current_song['played_at'].rstrip('Z'))
        previous_time = datetime.fromisoformat(previous_song['played_at'].rstrip('Z'))

        time_difference = (previous_time - current_time).total_seconds()

        #We only keep different consecutive songs and songs that have been played for at least 30 seconds
        if current_song['track']['id'] != previous_song['track']['id'] and time_difference >= 30:
            unique_songs.append(current_song)

    recently_played_songs = unique_songs
    return recently_played_songs

#if the user provides a "StreamingHistory.json" file, then we use this function to filter the listening history.
#we order the listening history by decreasing playing timestamp
#we remove consecutive duplicates and songs that have been played for less than 50% of the its duration
def filter_listening_history_file(csv_data):
    valid_items = []
    for item in csv_data:
        try:
            item['endTime'] = datetime.strptime(item['endTime'], "%Y-%m-%d %H:%M")
            valid_items.append(item)
        except ValueError:
            csv_data.remove(item)
    
    recently_played_songs = sorted(valid_items, key=lambda x: x['endTime'], reverse=True)
    unique_songs = [recently_played_songs[0]]

    for i in range(1, len(recently_played_songs)):
        current_song = recently_played_songs[i]
        previous_song = recently_played_songs[i - 1]
        
        listen_percentage = math.floor(100 * (int(current_song['msPlayed']) / int(current_song['msDuration'])))
        if current_song['TrackID'] != previous_song['TrackID'] and listen_percentage >= 50:
            unique_songs.append(current_song)

    recently_played_songs = unique_songs
    return recently_played_songs
