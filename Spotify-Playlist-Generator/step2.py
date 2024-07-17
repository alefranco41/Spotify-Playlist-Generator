import pickle
from step1 import check_listening_history_file, data_directory, most_similar_song_sets_suffix
from scipy.spatial.distance import euclidean #needed in the dynamic programming algorithm
from datetime import timedelta #manage timestamps of songs in order to compute listening history patterns
import random #choose a random listening history patterns
import os
import sys
from listening_history_manager import get_features, change_credentials, get_recommendations
#global variables
playlist_length = 48
best_history_patterns_suffix = "_best_history_patterns.bin"



#if, for a given day and a given hour, one or more listening history patterns are valid (i.e, if the pattern length is greater than playlist_length)
#we choose a random pattern (with greater probability for newer ones) as input for the dynamic programming algorithm
def choose_pattern_with_random_probability(patterns_with_enough_songs, timestamp_key):
    timestamps = [pattern[0][timestamp_key] for pattern in patterns_with_enough_songs]
    probabilities = [1 / (i + 1) for i in range(len(timestamps))]
    chosen_pattern = random.choices(patterns_with_enough_songs, weights=probabilities, k=1)[0]    
    return chosen_pattern

#if, for a given day and a given hour, no listening history patterns are valid (i.e, if none of the patterns have length greater than playlist_length)
#we overlap those patterns until we get a pattern with desired length.
def overlap_patterns(today_period_patterns, timestamp_key):
    chosen_pattern = []

    for pattern in today_period_patterns:
        chosen_pattern.extend(pattern)

    chosen_pattern.sort(key=lambda x: x[timestamp_key].time())
    return chosen_pattern

#if, for a given day and a given hour, no listening history patterns are valid (i.e, if none of the patterns have length greater than playlist_length
#and we can't overlap patterns, either beacause we don't have any patterns or because the sum of the length of the patterns is still lower than playlist_length
#we compute the closest pattern, by trying to apply the previous two functions to the patterns in descending order of dates.
def compute_closest_pattern(period,history_patterns, day_name, timestamp_key):
    ordered_patterns = sorted(history_patterns, key=lambda x: abs(x - period), reverse=True)
    chosen_pattern = None

    while ordered_patterns:
        playlist_length = 48
        patterns = history_patterns.get(ordered_patterns.pop(), None)
        today_period_patterns = patterns.get(day_name,None)
        if today_period_patterns:
            patterns_with_enough_songs = [pattern for pattern in today_period_patterns if len(pattern) > playlist_length]
            if patterns_with_enough_songs:
                chosen_pattern = choose_pattern_with_random_probability(patterns_with_enough_songs, timestamp_key)
            else:
                while playlist_length > 0 and not chosen_pattern:
                    if sum([len(pattern) for pattern in today_period_patterns]) >= playlist_length:
                        chosen_pattern = overlap_patterns(today_period_patterns, timestamp_key)
                    playlist_length -= 1
    
    return chosen_pattern
        
#since it is possible (and hopefully likely) that for a given day and a given hour we have more than one listening history pattern, we need to choose the "best" one.
#we do so by utilizing the three different functions previously described.
def compute_best_history_patterns(periods, timestamp_key, prefix_name):
    best_history_patterns = {}
    best_history_patterns_file_path = os.path.join(data_directory, prefix_name + best_history_patterns_suffix)

    try:
        if os.path.exists(best_history_patterns_file_path):
            with open(best_history_patterns_file_path, "rb") as file:
                best_history_patterns = pickle.load(file)
                print("Retrieved best history patterns")
                return best_history_patterns
    except Exception as e:
            print(e)
            pass
    
    history_patterns = compute_listening_history_patterns(periods, timestamp_key)

    
    for day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        for period, patterns in history_patterns.items():
            playlist_length = 48
            chosen_pattern = None
            today_period_patterns = patterns.get(day_name, None)
            if today_period_patterns:
                patterns_with_enough_songs = [pattern for pattern in today_period_patterns if len(pattern) >= playlist_length]
                if patterns_with_enough_songs:
                    chosen_pattern = choose_pattern_with_random_probability(patterns_with_enough_songs, timestamp_key)
                else:
                    while playlist_length > 0 and not chosen_pattern:
                        if sum([len(pattern) for pattern in today_period_patterns]) >= playlist_length:
                            chosen_pattern = overlap_patterns(today_period_patterns, timestamp_key)
                        playlist_length -= 1
            else:
                chosen_pattern = compute_closest_pattern(period,history_patterns, day_name, timestamp_key)
            
            if chosen_pattern:
                best_history_patterns[(day_name, period)] = chosen_pattern
    
    if not best_history_patterns:
        print(f"Couldn't generate history patterns for day {day_name} and hour {list(periods.keys())}")
        #sys.exit()
    else:
        with open(best_history_patterns_file_path,"wb") as file:
            pickle.dump(best_history_patterns, file)
    
    print("Generated history patterns")
    return best_history_patterns

#given a timestamp (i.e a day and an hour in which songs have been played), we compute the list of the listening history patterns.
#the way in which we determine the end of a pattern and the start of the following one is by exploiting the difference of the timestamp of two consecutive songs:
#if two consecutive songs have a difference in timestamp of 15 or more minutes, then we put those two songs in different patterns.
def compute_history_pattern_day_hour(periods, timestamp, timestamp_key):
    patterns = []
    current_pattern = []
    previous_timestamp = timestamp - timedelta(hours=1)
    tracks = sorted(periods[timestamp], key=lambda x: x[timestamp_key])

    #check if the last listening history pattern of the previous period has songs that end in the current period.
    #in that case, we start to compute the patterns of the current period from the song after the last song of the previous period that ended in the current period.
    previous_tracks = periods.get(previous_timestamp, None)
    first_track_index = None
    if previous_tracks:
        previous_tracks = sorted(previous_tracks, key=lambda x: x[timestamp_key])
        if tracks[0][timestamp_key] - previous_tracks[-1][timestamp_key] <= timedelta(minutes=15):
            first_track_index = next((i for i, track in enumerate(tracks) if track[timestamp_key] - tracks[i-1][timestamp_key] > timedelta(minutes=15)), None)
            if first_track_index is not None:
                tracks = tracks[first_track_index:]
            #else:
                #return patterns

    #compute the listening history patterns of the current period
    #before adding the last pattern to the list, we check if it ends in a following period
    for track in tracks:
        if not current_pattern or track[timestamp_key] - current_pattern[-1][timestamp_key] <= timedelta(minutes=15):
            current_pattern.append(track)
        else:
            patterns.append(current_pattern)
            current_pattern = [track]

    #check if the last pattern of the current period ends in one of the following periods.
    end_of_period = timestamp + timedelta(hours=1)
    last_period_song_timestamp = current_pattern[-1][timestamp_key].replace(tzinfo=None)
    while end_of_period - last_period_song_timestamp <= timedelta(minutes=15):
            end_of_period = timestamp + timedelta(hours=1)
            if end_of_period in periods:
                next_tracks = periods[end_of_period]
                next_tracks = sorted(next_tracks, key=lambda x: x[timestamp_key])
                for next_track in next_tracks:
                    if next_track[timestamp_key] - current_pattern[-1][timestamp_key] > timedelta(minutes=15):
                        break
                    current_pattern.append(next_track)
                    last_period_song_timestamp = current_pattern[-1][timestamp_key].replace(tzinfo=None)
                timestamp = end_of_period
            else:
                break
    
    patterns.append(current_pattern)
    return patterns


#function that computes the listening history patterns for every day and every hour in the listening history
def compute_listening_history_patterns(periods, timestamp_key):
    history_patterns = {}
    sorted_periods = sorted(periods.items(), key=lambda x: x[0], reverse=True)
    for hour in [i for i in range(0,24)]:
        history_patterns_days = {}
        for timestamp, tracks in sorted_periods:
            if timestamp.hour == hour:
                day = timestamp.strftime("%A")
                if not history_patterns_days.get(day, None):
                    history_patterns_days[day] = []
                
                history_patterns_days[day].extend(compute_history_pattern_day_hour(periods, timestamp, timestamp_key))
        history_patterns[hour] = history_patterns_days

    return history_patterns



#Dynamic programming algotithm that computes, for every playlist pattern, the best song ordering
def compute_optimal_solution_indexes(history_patterns, playlist_patterns):
    optimal_solutions_indexes = {}
    for period, playlist in playlist_patterns.items():
        if not history_patterns.get(period, None):
            continue
        spotify = change_credentials()

        if len(history_patterns[period]) > 100:
            history_pattern = []
            sublists = [history_patterns[period][i:i+100] for i in range(0, len(history_patterns[period]), 100)]

            for sublist in sublists:
                # Chiama la funzione get_features con la sotto-lista corrente
                features = get_features(sublist, spotify)
                # Aggiungi i risultati alla lista di tutti i risultati
                history_pattern.extend(features)

        else:
            history_pattern = get_features(history_patterns[period], spotify)
        
        playlist = get_features(playlist, spotify)

        m = len(playlist)
        k = len(history_pattern)

        if  k > m:    
            excess = k - m
            start_index = excess // 2
            end_index = start_index + k
            history_pattern = history_pattern[start_index:end_index]
            k = m

        M = []
        V = []

        M_first_row = [euclidean([value for value in history_pattern[0].values() if not isinstance(value, str)], [value for value in playlist[j].values() if not isinstance(value, str)]) for j in range(m)]
        V_first_row = [j for j in range(m)]
        
        M.append(M_first_row)
        V.append(V_first_row)

        for i in range(1,k):
            M_i_th_row = []
            V_i_th_row = []
            for j in range(m):
                distance = euclidean([value for value in history_pattern[i].values() if not isinstance(value, str)], [value for value in playlist[j].values() if not isinstance(value, str)])
                playlist_pattern_distances = [M[i-1][t] + abs((euclidean([value for value in history_pattern[i-1].values() if not isinstance(value, str)], [value for value in history_pattern[i].values() if not isinstance(value, str)]) - euclidean([value for value in playlist[t].values() if not isinstance(value, str)], [value for value in playlist[j].values() if not isinstance(value, str)]))) for t in range(m)]
                min_distance = min(playlist_pattern_distances)
                min_index = playlist_pattern_distances.index(min_distance)
                M_i_th_row.append(distance + min_distance)
                V_i_th_row.append(min_index)
                    
            M.append(M_i_th_row)
            V.append(V_i_th_row)

        #retrieve the optimal solution indexes
        min_value = min(M[k-1])
        min_index = M[k-1].index(min_value)
        vertices_period = [min_index]

        duplicate_indexes = [0]
        for i in range(k-2, -1, -1):
            t = vertices_period[0]
            min_index = V[i+1][t]
            if min_index in vertices_period:
                duplicate_indexes.insert(0,1)
            else:
                duplicate_indexes.insert(0,0)
            vertices_period.insert(0, min_index)
        optimal_solutions_indexes[period] = (vertices_period,duplicate_indexes)
    if not optimal_solutions_indexes:
        print(f"Couldn't run the dynamic programming algorithm for hours {list(playlist_patterns.keys())}")
            
    print(f"Computed the optimal ordering of the song-sets produced for hours {list(playlist_patterns.keys())}")
    return optimal_solutions_indexes




#given the optimal song ordering indexes, retrieve, for every period, the actual song ids
def retrieve_optimal_solution_songs(optimal_solutions_indexes, playlist_patterns):
    playlists = {}
    
    for period, songs in playlist_patterns.items():
        if optimal_solutions_indexes.get(period, None):
            vertices_period = optimal_solutions_indexes[period][0]
            duplicate_indexes = optimal_solutions_indexes[period][1]

            n_duplicate_indexes = len([index for index in duplicate_indexes if index == 1])
            playlist_length = len(vertices_period)
            
            playlist = [songs[index]['id'] for index in vertices_period]
            
            print(f"Removing duplicate indexes from the optimal song ordering for period: {period}...")
            j=0
            for i in range(playlist_length):
                if i == 0 or i == 1: 
                    track_ids = playlist[0:min(5, len(playlist))]
                elif i == len(playlist) - 1 or i == len(playlist) - 2: 
                    track_ids = playlist[max(0, len(playlist) - 5):]
                else:
                    track_ids = [playlist[max(0, i-2)], playlist[max(0, i-1)], playlist[i], playlist[min(len(playlist) - 1, i+1)], playlist[min(len(playlist) - 1, i+2)]]

                if duplicate_indexes[i]:
                    j+=1
                    if j % 10 == 0 or j == 1:
                        spotify = change_credentials()

                    print(f"Getting recommendation for duplicate track '{[playlist[i]]}'")
                    recommendations = get_recommendations(spotify=spotify, seed_tracks=track_ids, limit=100).get('tracks')

                    for recommendation in recommendations:
                        if recommendation['id'] not in playlist:
                            playlist[i] = recommendation['id']
                            break

            print(f"Optimal song ordering for period {period}: {playlist}")
            playlists[period] = playlist

    if not playlists:
        print(f"Couldn't retrieve the optimal solution songs for hours {list(playlist_patterns.keys())}")
        #sys.exit()

    return playlists


def create_playlists_dict(final_playlist, history_patterns, prefix_name, method_name):
    playlists = {}
    for period, playlist in final_playlist.items():
        print(playlist)
        playlists[(prefix_name,period[0],period[1],method_name)] = (playlist,history_patterns[(period[0],period[1])])

    with open("data/playlists.bin", "ab") as file:
        pickle.dump(playlists, file)
    print("Playlists uploaded on data/playlists.bin")

    return playlists

#upload the playlists generated for every period on Spotify
def create_playlists(playlists):
    spotify = change_credentials()
    user_id = spotify.me()['id']
    for playlist_data, tracks in playlists.items():
        playlist_name = f"{playlist_data[1]} {playlist_data[2]}:00"
        
        while True:
            try:
                playlist = spotify.user_playlist_create(user=user_id, name=playlist_name)
                spotify.playlist_add_items(playlist['id'], tracks[0])
                break
            except Exception as e:
                print(e)
                spotify = change_credentials()

        
        print(f"Playlist uploaded on Spotify")

def get_timestamp_key(periods):
    #check if the module 'step1' is running with a "StreamingHistory.json" file provided by the user or not.
    #this check is needed because the timestamp keys in the dictionary 'periods' will be different.
    if check_listening_history_file(periods):
        timestamp_key = 'endTime'
    else:
        timestamp_key = 'played_at'
    return timestamp_key

