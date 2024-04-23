import numpy as np
from evaluation import retrieve_playlists
from listening_history_manager import get_features, change_credentials
import random
import os
import pickle
from step1 import compute_prefix_name, check_listening_history_file
import math


genres = ['acoustic', 'afrobeat', 'alt-rock', 'alternative', 'ambient', 'anime', 'black-metal', 'bluegrass', 'blues', 'bossanova',
          'brazil', 'breakbeat', 'british', 'cantopop', 'chicago-house', 'children', 'chill', 'classical', 'club', 'comedy',
          'country', 'dance', 'dancehall', 'death-metal', 'deep-house', 'detroit-techno', 'disco', 'disney', 'drum-and-bass', 'dub',
          'dubstep', 'edm', 'electro', 'electronic', 'emo', 'folk', 'forro', 'french', 'funk', 'garage',
          'german', 'gospel', 'goth', 'grindcore', 'groove', 'grunge', 'guitar', 'happy', 'hard-rock', 'hardcore', 'hardstyle', 'heavy-metal',
          'hip-hop', 'holidays', 'honky-tonk', 'house', 'idm', 'indian', 'indie', 'indie-pop', 'industrial', 'iranian', 'j-dance', 'j-idol',
          'j-pop', 'j-rock', 'jazz', 'k-pop', 'kids', 'latin', 'latino', 'malay', 'mandopop', 'metal', 'metal-misc', 'metalcore', 'minimal-techno',
          'movies', 'mpb', 'new-age', 'new-release', 'opera', 'pagode', 'party', 'philippines-opm', 'piano', 'pop', 'pop-film',
          'post-dubstep', 'power-pop', 'progressive-house', 'psych-rock', 'punk', 'punk-rock', 'r-n-b', 'rainy-day', 'reggae', 'reggaeton',
          'road-trip', 'rock', 'rock-n-roll', 'rockabilly', 'romance', 'sad', 'salsa', 'samba', 'sertanejo', 'show-tunes', 'singer-songwriter',
          'ska', 'sleep', 'songwriter', 'soul', 'soundtracks', 'spanish', 'study', 'summer', 'swedish', 'synth-pop', 'tango', 'techno', 'trance',
          'trip-hop', 'turkish', 'work-out', 'world-music']


def normalize_vector(vector):
    # Calcola la somma di tutti gli elementi nel vettore
    total_sum = sum(vector)
    
    # Normalizza ciascun elemento del vettore
    normalized_vector = [element / total_sum for element in vector]
    
    return normalized_vector


def entropy(vector):
    # Calcola l'entropia del vettore
    entropy_value = -sum(p * math.log(p) for p in vector if p > 0)
    
    return entropy_value


def compute_average_entropy(features_list):
    entropies = []
    for features in features_list:
        normalized_features = normalize_vector(features)
        e = entropy(normalized_features)
        entropies.append(e)
    
    # Calcola la media delle entropie
    average_entropy = sum(entropies) / len(entropies)
    
    return average_entropy


def compute_average_features_distance():
    playlists = retrieve_playlists()
    spotify = change_credentials()

    keys = list(playlists.keys())
    random.shuffle(keys)
    playlists = {key: playlists[key] for key in keys}

    count = 0
    average_entropy_step_1 = 0
    average_entropy_hyb_1 = 0
    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        if playlist_data[3] == "our_method":
            hyb_1_playlist = playlists.get((playlist_data[0], playlist_data[1], playlist_data[2], "hyb-1"), None)
            if hyb_1_playlist:          
                step_1_features = [[v for v in features.values() if not isinstance(v,str)] for features in get_features(generated_playlist, spotify)]
                hyb_1_features = [[v for v in features.values() if not isinstance(v,str)] for features in get_features(hyb_1_playlist[0], spotify)]

                average_entropy_step_1 += compute_average_entropy(step_1_features)
                average_entropy_hyb_1 += compute_average_entropy(hyb_1_features)
                count += 1

                all_average_entropy_step_1 = average_entropy_step_1 / count
                all_average_entropy_hyb_1 = average_entropy_hyb_1 / count
                print(all_average_entropy_step_1, all_average_entropy_hyb_1)
        else:
            continue


def compute_average_listening_habits_distance():
    skiplist = ['LH25', 'LH26']
    periods = {}

    listening_history_habits = {}
    for file in os.listdir("data"):
        if file.endswith("habits.bin"):
            prefix_name = compute_prefix_name(file).strip("listeninghabits")
            if prefix_name not in skiplist:
                with open(os.path.join("data", file), "rb") as file:
                    history_habits = pickle.load(file)
                    listening_history_habits[prefix_name] = history_habits
    step_1_song_sets_habits = {}
    for file in os.listdir("data"):
        if file.endswith("song_sets.bin"):
            prefix_name = compute_prefix_name(file).strip("mostsimilarsongsets")
            if prefix_name not in skiplist:
                with open(os.path.join("data", prefix_name + "_periods.bin"), "rb") as periods_file:
                    periods[prefix_name] = pickle.load(periods_file)

                with open(os.path.join("data", file), "rb") as songsets_file:
                    song_sets = pickle.load(songsets_file)
                    step_1_song_sets_habits[prefix_name] = compute_song_sets_listening_habits(periods[prefix_name], song_sets)
                    print(step_1_song_sets_habits[prefix_name])
    
    with open("data/playlists.bin", "rb") as file:
        playlists = {}
        while True:
            try:
                playlists.update(pickle.load(file))
            except EOFError:
                break
    
    hyb_1_song_sets_habits = {}
    playlists = {key:value for key,value in playlists.items() if key[0] not in skiplist and key[0] in list(periods.keys()) and key[3] == 'hyb-1'}
    total = len(playlists)

    i = 1
    for (prefix_name, day, hour, method), (generated_playlist, playlist_pattern) in playlists.items():
        print(f"PROGRESS: {round(100*(i)/total, 2)}%")
        i += 1
        if not hyb_1_song_sets_habits.get(prefix_name, None):
            hyb_1_song_sets_habits[prefix_name] = {}
            
        if not hyb_1_song_sets_habits[prefix_name].get(hour, None):
            hyb_1_song_sets_habits[prefix_name][hour] = []
            
        hyb_1_song_sets_habits[prefix_name][hour].append(compute_song_set_listening_habits(periods[prefix_name], generated_playlist))
        print(hyb_1_song_sets_habits[prefix_name][hour])

    with open("data/all_listening_habits.bin", "wb") as listening_habits:
        pickle.dump((listening_history_habits, step_1_song_sets_habits, hyb_1_song_sets_habits), listening_habits)


def compute_song_sets_listening_habits(periods, song_sets):
    listening_habits = {}
    for hour, tracks_song_set in song_sets.items():
        ntna = 0
        ntka = 0
        h = 0
        for track_item_song_set in tracks_song_set:
            h += 1
            track_song_set_id = track_item_song_set['id']
            track_song_set_artist = track_item_song_set['artists'][0]['id']

            if check_listening_history_file(periods):
                try:
                    history_ids = [track_item_history['TrackID'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
                    history_artists = [track_item_history['artistName'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]
                    track_song_set_artist = track_item_song_set['artists'][0]['name']
                except KeyError:
                    history_ids = [track_item_history['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
                    history_artists = [track_item_history['artists'][0]['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]
            else:
                history_ids = [track_item_history['track']['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
                history_artists = [track_item_history['track']['artists'][0]['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]
            
            print(track_song_set_id, history_ids)
            print(track_song_set_artist, history_artists)
            if track_song_set_id not in history_ids and track_song_set_artist not in history_artists:
                ntna += 1
            elif track_song_set_id not in history_ids and track_song_set_artist in history_artists:
                ntka += 1

        listening_habits[hour] = (100*ntna/h,100*ntka/h)
    return listening_habits



def compute_song_set_listening_habits(periods, song_set):
    ntna = 0
    ntka = 0
    h = 0
    while True:
        try:
            spotify = change_credentials()
            if len(song_set) > 50:
                sublists = [song_set[i:i+50] for i in range(0, len(song_set), 50)]
                song_set = []
                for sublist in sublists:
                    tracks = spotify.tracks(sublist)['tracks']
                song_set.extend(tracks)
            else:
                song_set = spotify.tracks(song_set)['tracks']
        except Exception:
            spotify = change_credentials()
        else:
            break

            

    for track_item_song_set in song_set:
        h += 1
        track_song_set_id = track_item_song_set['id']
        track_song_set_artist = track_item_song_set['artists'][0]['id']

        if check_listening_history_file(periods):
            try:
                history_ids = [track_item_history['TrackID'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
                history_artists = [track_item_history['artistName'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]
            except KeyError:
                history_ids = [track_item_history['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
                history_artists = [track_item_history['artists'][0]['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]
        else:
            history_ids = [track_item_history['track']['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
            history_artists = [track_item_history['track']['artists'][0]['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]
        if track_song_set_id not in history_ids and track_song_set_artist not in history_artists:
            ntna += 1
        elif track_song_set_id not in history_ids and track_song_set_artist in history_artists:
            ntka += 1

    return (100*ntna/h,100*ntka/h)


def euclidean_distance(vector1, vector2):
    return np.linalg.norm(np.array(vector1) - np.array(vector2)) / np.linalg.norm(np.array(vector2))


def cosine_similarity(vector1, vector2):
    dot_product = np.dot(vector1, vector2)
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)

    if norm1 == 0 or norm2 == 0:
        return np.nan
    
    similarity = dot_product / (norm1 * norm2)
    return similarity

def retrieve_all_listening_habits():
    with open("data/all_listening_habits.bin", "rb") as file:
        listening_history_habits, step_1_song_sets_habits, hyb_1_song_sets_habits = pickle.load(file)

    count_hyb = 0
    count_step = 0
    sum_similarity_hyb = 0
    sum_similarity_step = 0
    count_nan_hyb = 0
    count_nan_step = 0
    count_ex_step = 0
    count_ex_hyb = 0
    for key in listening_history_habits:
        for hour in listening_history_habits[key]:
            vector_listening_history = [listening_history_habits[key][hour][0], listening_history_habits[key][hour][1]]

            try:
                vector_step_1 = [step_1_song_sets_habits[key][hour][0], step_1_song_sets_habits[key][hour][1]]
            except Exception:
                count_ex_step += 1
                pass
            else:
                distance_step = cosine_similarity(vector_step_1, vector_listening_history)
                if not np.isnan(distance_step):
                    count_step += 1
                    sum_similarity_step += distance_step
                else:
                    count_nan_step += 1
                average_distance_step = sum_similarity_step / count_step

            
            try:
                vector_habits = hyb_1_song_sets_habits[key][hour]
            except Exception:
                count_ex_hyb += 1
                pass
            else:
                for habits in vector_habits:
                    distance_hyb = cosine_similarity([habits[0], habits[1]], vector_listening_history)
                    if not np.isnan(distance_hyb):
                        count_hyb += 1
                        sum_similarity_hyb += distance_hyb
                    else:
                        count_nan_hyb += 1
                average_distance_hyb = sum_similarity_hyb / count_hyb
    print(average_distance_step,average_distance_hyb)
    

def flatten(lst):
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list


def get_tracks(song_set):
    while True:
        try:
            spotify = change_credentials()
            if len(song_set) > 50:
                sublists = [song_set[i:i+50] for i in range(0, len(song_set), 50)]
                song_set = []
                for sublist in sublists:
                    tracks = spotify.tracks(sublist)['tracks']
                    tracks_artists= list(set([track['artists'][0]['id'] for track in tracks]))
                song_set.extend(tracks_artists)
            else:
                tracks = spotify.tracks(song_set)['tracks']
                tracks_artists = list(set([track['artists'][0]['id'] for track in tracks]))
                song_set = tracks_artists
                
        except Exception as e:
            spotify = change_credentials()
        else:
            break
    return song_set

def compute_different_artists_and_genres():
    playlists = retrieve_playlists()
    spotify = change_credentials()


    keys = list(playlists.keys())
    random.shuffle(keys)
    playlists = {key: playlists[key] for key in keys}

    count = 1
    av_artists_step_1 = 0
    av_artists_hyb_1 = 0
    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        if playlist_data[3] == "our_method":
            hyb_1_playlist = playlists.get((playlist_data[0], playlist_data[1], playlist_data[2], "hyb-1"), None)
            if hyb_1_playlist and len(generated_playlist) >= 48:
                    
                step_1_playlist_tracks = get_tracks(generated_playlist)
                hyb_1_playlist_tracks = get_tracks(hyb_1_playlist[0]) 

                try:
                    history_pattern_tracks = get_tracks([track['track_id'] for track in history_pattern])
                except KeyError:
                    try:
                        history_pattern_tracks = get_tracks([track['TrackID'] for track in history_pattern])
                    except KeyError:
                        history_pattern_tracks = get_tracks([track['id'] for track in history_pattern])

                print(len(set(step_1_playlist_tracks).intersection(set(history_pattern_tracks))),len(set(step_1_playlist_tracks).union(set(history_pattern_tracks))))
                av_artists_step_1 += len(set(step_1_playlist_tracks).intersection(set(history_pattern_tracks))) / len(set(step_1_playlist_tracks).union(set(history_pattern_tracks)))
                av_artists_hyb_1 += len(set(hyb_1_playlist_tracks).intersection(set(history_pattern_tracks))) / len(set(hyb_1_playlist_tracks).union(set(history_pattern_tracks)))

                print(len(generated_playlist), len(hyb_1_playlist[0]))
                all_av_artists_step_1 = av_artists_step_1 / count 
                all_av_artists_hyb_1 = av_artists_hyb_1 / count

                print(all_av_artists_step_1, all_av_artists_hyb_1)
                count += 1
        else:
            continue


compute_average_listening_habits_distance()