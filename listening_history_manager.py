import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy


#Spotify application credentials
client_id = '73962f02bb8e47ceb4f7542c7c6ce258'
client_secret = '05775486ab0747e99544078d539e57ce'
redirect_uri = 'https://www.google.com'

#interact with the spotify API
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope="playlist-modify-public user-read-recently-played"))

#try to load the accumulated listening history (spotify API only allows to retrieve the last 50 songs of the listening history)
try:
    with open("history.bin", "rb") as file:
        recently_played_songs = pickle.load(file)
except FileNotFoundError:
    recently_played_songs = {'items': []}

existing_song_keys = {(item['track']['id'], item['played_at']) for item in recently_played_songs['items']}

#get the last 50 songs in the listening history and keep only the ones that have not been stored yet
new_songs = [song for song in spotify.current_user_recently_played()['items'] if (song['track']['id'], song['played_at']) not in existing_song_keys]

#add to the existing songs in the playlist the new ones
recently_played_songs['items'].extend(new_songs)


with open("history.bin", "wb") as file:
    pickle.dump(recently_played_songs, file)

#order the listening history by decreasing playing timestamp
recently_played_songs = sorted(recently_played_songs['items'], key=lambda x: x['played_at'], reverse=True)

#remove consecutive duplicates
unique_songs = [recently_played_songs[0]] 
for i in range(1, len(recently_played_songs)):
    if recently_played_songs[i]['track']['id'] != recently_played_songs[i - 1]['track']['id']:
        unique_songs.append(recently_played_songs[i])

recently_played_songs = unique_songs
