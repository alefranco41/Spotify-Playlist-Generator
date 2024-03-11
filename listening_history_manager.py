import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy


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

#remove consecutive duplicates
unique_songs = [recently_played_songs[0]] 
for i in range(1, len(recently_played_songs)):
    if recently_played_songs[i]['track']['id'] != recently_played_songs[i - 1]['track']['id']:
        unique_songs.append(recently_played_songs[i])

recently_played_songs = unique_songs
