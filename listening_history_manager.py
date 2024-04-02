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
        'client_id':'88af6dfe58a24ae5afd36cd35cff978c',
        'client_secret':'84202b1ec08442dea6899e16214d8242',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'69dddf2b92de442ab9af0b8910c36b01',
        'client_secret':'eb9d3663520446e99ca89ce0ca8da4ae',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'f95642ced4744ba89b32c0cb22629c0e',
        'client_secret':'0e1db2d43493486c97acb6ad07db3a36',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'149c7e56cf274adcaf2e57da5641f84c',
        'client_secret':'7ed5a6a8c6f449f099d3cc3cd62fba6c',
        'redirect_uri':'https://www.google.com'
    },

    {
        'client_id':'b45b91203a334848ae2a6895e695fb56',
        'client_secret':'c53c8201ba8447f0b559e62ef142f310',
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
