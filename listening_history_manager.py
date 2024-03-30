import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime
import math
import random
import os

if os.path.exists('.cache'):
    os.remove('.cache')

#Spotify application credentials
credentials_dicts = [
    {
    'client_id':'20e93cf42c624e6f863e1a55230fee16',
    'client_secret':'b6df3671c90c4fbbbb8a103aa666ef2d',
    'redirect_uri':'https://www.google.com'
    },

    {
    'client_id':'b128c6e5f09d4109b196802bfa79b6e9',
    'client_secret':'312b80d3a986451f8b873f9f4224b2e3',
    'redirect_uri':'https://www.google.com'
    },

    {
    'client_id':'7e468553e67546489bad49bf5c2589be',
    'client_secret':'46442df48124489fb6bc86a814e24300',
    'redirect_uri':'https://www.google.com'
    },

    {
    'client_id':'17bda904787947c099271407b49da1c4',
    'client_secret':'c41d4c247f1e47deb12a5c3aa168c458',
    'redirect_uri':'https://www.google.com'
    },

    {
    'client_id':'3f4594acd88840be805732c54f957a03',
    'client_secret':'0411e4dd5f254fe5af656ea7067b1729',
    'redirect_uri':'https://www.google.com'
    }
]

random_credentials = random.choice(credentials_dicts)


#interact with the spotify API
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**random_credentials, scope="playlist-modify-private user-read-recently-played"))

#try to load the accumulated listening history (spotify API only allows to retrieve the last 50 songs of the listening history)
try:
    with open("recently_played_songs.bin", "rb") as file:
        recently_played_songs = pickle.load(file)
except FileNotFoundError:
    recently_played_songs = {'items': []}

existing_song_keys = {(item['track']['id'], item['played_at']) for item in recently_played_songs['items']}

#get the last 50 songs in the listening history and keep only the ones that have not been stored yet
new_songs = [song for song in spotify.current_user_recently_played()['items'] if (song['track']['id'], song['played_at']) not in existing_song_keys]

#add to the existing songs in the playlist the new ones
recently_played_songs['items'].extend(new_songs)


with open("recently_played_songs.bin", "wb") as file:
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
