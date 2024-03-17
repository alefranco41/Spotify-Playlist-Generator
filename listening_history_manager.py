import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime
#Spotify application credentials
client_id = '20e93cf42c624e6f863e1a55230fee16'
client_secret = 'b6df3671c90c4fbbbb8a103aa666ef2d'
redirect_uri = 'https://www.google.com'

#interact with the spotify API
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope="playlist-modify-private user-read-recently-played"))

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

