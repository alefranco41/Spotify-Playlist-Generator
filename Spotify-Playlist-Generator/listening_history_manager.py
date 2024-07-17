import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime, timedelta
import math
import random
import os
from custom_cache_handler import CustomCacheFileHandler
import pytz #convert Spotify's time zone to the current one
import csv
import json
import requests
from tzlocal import get_localzone #get current time zone

data_folder = "data"
cache_folder = "cache"
feature_names_to_remove = ["uri", "track_href", "analysis_url", "type", "duration_ms"] #track features not needed for clustering
feature_names_1 = ['Acousticness','Danceability','Energy','Instrumentalness','Key','Liveness','Loudness','Mode','Speechiness','Tempo','Time_signature','Valence','TrackID']
keys_ordering =  ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'id', 'time_signature']


#Spotify application credentials
credentials_dicts = {
    '': [
            {
                'client_id':'',
                'client_secret':'',
                'redirect_uri':''
            },
            {
                'client_id':'',
                'client_secret':'',
                'redirect_uri':''
            }, 
            {
                'client_id':'',
                'client_secret':'',
                'redirect_uri':''
            }, 
            {
                'client_id':'',
                'client_secret':'',
                'redirect_uri':''
            }, 
            {
                'client_id':'',
                'client_secret':'',
                'redirect_uri':''
            }, 
    ]
}


if not os.path.exists(data_folder):
    os.makedirs(data_folder)

if not os.path.exists(cache_folder):
    os.makedirs(cache_folder)


#convert the "StreamingHistory.json" file provided by the user in a list of dictionaries.
def csv_to_dict(csv_file):
    data = []
    try:
        if os.path.isdir(csv_file):
            for file in os.listdir(csv_file):
                file_path = os.path.join(csv_file, file)
                if os.path.isfile(file_path) and file_path.endswith(".json"):
                    with open(file_path, 'r') as file:
                        json_data = json.load(file)
                        for song_data in json_data:
                            data.append(song_data)
        else:
            with open(csv_file, 'r') as file:
                reader = csv.reader(file, delimiter=';')
                keys = next(reader)  
                for row in reader:
                    data.append(dict(zip(keys, row)))
    except Exception as e:
        print(e)
        data = []
        print(f"An error occurred while trying to load data from file {csv_file}.")
    else:
        if data:
            data = filter_listening_history_file(data)
            print(f"Succesfully filtered the listening history: {csv_file}")

    return data


def check_features(tracks, feature_names):
    all_features = True
    feature_list = []

    for track in tracks:
        features_track = {}
        for feature_name in feature_names:
            if feature_name == 'speechness':
                features_track['speechiness'] = track.get(feature_name, None)
                if not features_track['speechiness']:
                    all_features = False
                    break
            elif feature_name == 'TrackID':
                features_track['id'] = track.get(feature_name, None)
                if not features_track['id']:
                    all_features = False
                    break
            else:
                features_track[feature_name.lower()] = track.get(feature_name, None)
                if not features_track[feature_name.lower()]:
                    all_features = False
                    break

        if not all_features:
            feature_list = []
            break
        else:
            feature_list.append(features_track)

    return all_features, feature_list

#get the track features needed in the dynamic programming algorithm
def get_features(tracks, spotify):
    spotify = change_credentials()
    if isinstance(tracks[0], str):       
        ids = tracks
    else:
        all_features, feature_list = check_features(tracks, feature_names_1)
        if not all_features:
            if tracks[0].get('track', None):
                ids = [track['track']['id'] for track in tracks]
            elif tracks[0].get('TrackID', None):
                ids = [track['TrackID'] for track in tracks]
            else:
                ids = [track['id'] for track in tracks]
        else:
            feature_list = [{key: track[key] for key in keys_ordering} for track in feature_list]
            return feature_list
    
    if len(ids) > 50:
       sublists = [ids[i:i+50] for i in range(0, len(ids), 50)]
       features = [] 
       for sublist in sublists:
           while True:
                try:
                    features.extend(spotify.audio_features(tracks=sublist))
                except Exception as e:
                    print(e)
                    spotify = change_credentials()
                else:
                   break
                
    else:
        while True:
            try:
                features = spotify.audio_features(tracks=ids)
            except Exception as e:
                print(e)
                spotify = change_credentials()
            else:
                break
    feature_list = []
    for feature in features:
        if feature:
            track_features = feature.get('id', None)
            if track_features:
                final_features = dict(filter(lambda item: item[0] not in feature_names_to_remove, feature.items()))
                feature_list.append(final_features)

    return feature_list


def get_tracks(songs, timestamps, spotify):
    sublists = [songs[i:i+50] for i in range(0, len(songs), 50)]

    timestamp_sublists = [timestamps[i:i+50] for i in range(0, len(timestamps), 50)]

    songs = []
    for i,sublist in enumerate(sublists):
        while True:
            try:
                print(f"Retrieving song data for sublist #{i+1}/{len(sublists)}:")
                track_ids = [track['TrackID'] for track in sublist]
                tracks = spotify.tracks(track_ids)['tracks']
                if timestamp_sublists:
                    for j, track in enumerate(tracks):
                        track['endTime'] = timestamp_sublists[i][j]
                
                songs.extend(tracks)
                spotify = change_credentials()
            except Exception as e:
                print(e)
                spotify = change_credentials()
            else:
                break
    return songs


def compute_recently_played_songs(spotify):
    # Prova a caricare lo storico delle canzoni ascoltate (Spotify API permette solo di recuperare le ultime 50 canzoni)
    recently_played_songs = {'items': []}
    try:
        if os.path.exists("data/recently_played_songs.bin"):
            with open("data/recently_played_songs.bin", "rb") as file:
                recently_played_songs = pickle.load(file)
    except Exception:
        pass

    existing_song_keys = set()
    for item in recently_played_songs['items']:
        if isinstance(item['played_at'], str):
            timestamp = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
            timestamp = pytz.utc.localize(timestamp)
            timestamp = timestamp.astimezone(get_localzone())
            item['played_at'] = timestamp
        key = (item['track']['id'], item['played_at'])
        existing_song_keys.add(key)

    # Ottieni le ultime 50 canzoni ascoltate e mantieni solo quelle che non sono ancora state salvate
    new_songs = spotify.current_user_recently_played()['items']
    for song in new_songs:
        timestamp = datetime.strptime(song['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = pytz.utc.localize(timestamp)
        timestamp = timestamp.astimezone(get_localzone())
        song['played_at'] = timestamp

    new_songs = [song for song in new_songs if (song['track']['id'], song['played_at']) not in existing_song_keys]

    # Aggiungi le nuove canzoni alle esistenti
    recently_played_songs['items'].extend(new_songs)

    # Salva lo storico delle canzoni ascoltate
    with open("data/recently_played_songs.bin", "wb") as file:
        pickle.dump(recently_played_songs, file)

    # Ordina lo storico delle canzoni ascoltate per timestamp decrescente
    recently_played_songs['items'] = sorted(recently_played_songs['items'], key=lambda x: x['played_at'], reverse=True)
    #remove consecutive duplicates and songs that have been played for too little time
    unique_songs = [recently_played_songs['items'][0]]

    for i in range(1, len(recently_played_songs['items'])):
        current_song = recently_played_songs['items'][i]
        previous_song = recently_played_songs['items'][i - 1]

        #Compute the difference of the two timestamps
        if isinstance(current_song['played_at'], str):
            current_time = datetime.fromisoformat(current_song['played_at'].rstrip('Z'))
        else:
            current_time = current_song['played_at']

        if isinstance(previous_song['played_at'], str):
            previous_time = datetime.fromisoformat(previous_song['played_at'].rstrip('Z'))
        else:
            previous_time = previous_song['played_at']

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
            if item.get('date', None) and item.get('datetime', None):
                date_str = item['date']
                datetime_str = item['datetime']
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y")

                time_obj = datetime.strptime(datetime_str, "%H:%M:%S").time()
                combined_datetime = datetime.combine(date_obj, time_obj)
                item['endTime'] = combined_datetime
                item['TrackID'] = item['track_id']
                item['artistName'] = item['artist_name']
                item['trackName'] = item['track_name']
            elif item.get('endTime', None):
                item['endTime'] = datetime.strptime(item['endTime'], "%Y-%m-%d %H:%M")
                item['endTime'] = item['endTime'] - timedelta(milliseconds=int(item['msPlayed']))
            elif item.get('ts', None):
                timestamp = datetime.fromisoformat(item['ts'].rstrip('Z'))
                timestamp = pytz.utc.localize(timestamp)
                timestamp = timestamp.astimezone(get_localzone())
                item['endTime'] = timestamp
                item['TrackID'] = item['spotify_track_uri'].split(':')[-1]
            valid_items.append(item)
        except Exception as e:
            csv_data.remove(item)
    
    recently_played_songs = sorted(valid_items, key=lambda x: x['endTime'], reverse=True)
    unique_songs = [recently_played_songs[0]]

    for i in range(1, len(recently_played_songs)):
        current_song = recently_played_songs[i]
        previous_song = recently_played_songs[i - 1]
        
        listen_percentage = 0
        seconds_listened = 0
        try:
            listen_percentage = math.floor(100 * (int(current_song['msPlayed']) / int(current_song['msDuration'])))
        except KeyError:
            seconds_listened = (previous_song['endTime'] - current_song['endTime']).total_seconds()
        if current_song['TrackID'] != previous_song['TrackID'] and (listen_percentage >= 50 or seconds_listened >= 30):
            unique_songs.append(current_song)

    recently_played_songs = unique_songs
    return recently_played_songs

def print_in_box(text):
    border = '+' + '-' * (len(text) + 2) + '+'
    print(border)
    print(f"| {text} |")
    print(border)


def change_credentials():
    
    while True:
        try:
            random_account, random_account_credentials = random.choice(list(credentials_dicts.items()))
            random_credentials = random.choice(random_account_credentials)
            account_index = list(credentials_dicts.keys()).index(random_account)
            credentials_index = random_account_credentials.index(random_credentials)
            credentials_index_complete = account_index * len(random_account_credentials) + credentials_index
            custom_cache_handler = CustomCacheFileHandler(credentials_index=credentials_index_complete)
            print_in_box(f"ACCOUNT EMAIL: {random_account}")
            print_in_box(f"ACCOUNT CLIENT-ID: {random_credentials['client_id']}")
            spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**random_credentials, scope="playlist-modify-private playlist-modify-public user-read-recently-played", cache_handler=custom_cache_handler))
            #prova = spotify.current_user()['id']
        except spotipy.exceptions.SpotifyException as e:
            print(e)
            if e.http_status == 429:
                with open("data/errors.txt", "a") as file:
                    retry_after = int(e.headers.get('Retry-After'))
                    file.write(random_credentials['client_id'] + retry_after + "\n")
            continue
        except (spotipy.oauth2.SpotifyOauthError, TimeoutError, requests.exceptions.ReadTimeout) as e:
            print(e)
            continue
        else:
            break
    
    return spotify

def update_all_cache_files():
    with open("data/errors.txt", "a") as file:
        for email, apps in credentials_dicts.items():
            for app in apps:
                account_index = list(credentials_dicts.keys()).index(email)
                credentials_index = apps.index(app)
                credentials_index_complete = account_index * len(apps) + credentials_index
                custom_cache_handler = CustomCacheFileHandler(credentials_index=credentials_index_complete)
                print_in_box(f"ACCOUNT EMAIL: {email}")
                print_in_box(f"ACCOUNT CLIENT-ID: {app['client_id']}")
                try:
                    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**app, scope="playlist-modify-private user-read-recently-played", cache_handler=custom_cache_handler))
                    user_id = spotify.current_user()['id']
                except spotipy.SpotifyException as e:
                    if e.http_status == 429:
                        retry_after = int(e.headers.get('Retry-After'))
                        print(f"Too Many Requests. Retrying after {retry_after} seconds...")
                        continue
                    else:
                        print("Errore:", e)
                        file.write(app['client_id'])
                        file.write("\n")
                        file.write(str(e))
                        file.write("\n")
                        file.write("\n")
                        continue
                except Exception as e:
                    print(e)
                    file.write(app['client_id'])
                    file.write("\n")
                    file.write(str(e))
                    file.write("\n")
                    file.write("\n")
                    continue


def get_recommendations(spotify=change_credentials(), seed_tracks=None, limit=100, kwargs=None):
    while True:
        try:
            ret = spotify.recommendations(seed_tracks=seed_tracks, limit=limit, kwargs=kwargs)
        except spotipy.exceptions.SpotifyException:
            return []
        except Exception as e:
            print(e)
            change_credentials()
        else:
            break

    return ret