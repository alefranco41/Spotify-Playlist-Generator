import pickle
from step1 import hours, feature_names_to_remove
from scipy.spatial.distance import euclidean
from listening_history_manager import spotify
from datetime import datetime, timedelta
import random


song_sets_file_path = "most_similar_song_set.bin"
periods_file_path = "periods.bin"
playlist_length = 30
today_day_name = datetime.now().strftime("%A")

#retrieve the listening history and the song sets generated in the first step
def retrieve_data():
    song_sets = None
    periods = None
    with open(song_sets_file_path, "rb") as file:
        song_sets = pickle.load(file)

    with open(periods_file_path, "rb") as file:
        periods = pickle.load(file)

    print("Retrieved the listening history and the song sets generated from the previous step")
    return song_sets, periods



def choose_pattern_with_random_probability(patterns_with_enough_songs):
    timestamps = [pattern[0]['played_at'] for pattern in patterns_with_enough_songs]
    probabilities = [1 / (i + 1) for i in range(len(timestamps))]
    chosen_pattern = random.choices(patterns_with_enough_songs, weights=probabilities, k=1)
    return chosen_pattern[0]


def overlap_patterns(today_period_patterns):
    chosen_pattern = []

    i = len(today_period_patterns) - 1
    while len(chosen_pattern) < playlist_length:
        chosen_pattern.extend(today_period_patterns[i])
        i -= 1
    
    chosen_pattern.sort(key=lambda x: x['played_at'].time())
    chosen_pattern = chosen_pattern[:playlist_length]

    return chosen_pattern

def compute_closest_pattern(period,history_patterns, day_name):
    ordered_patterns = sorted(history_patterns, key=lambda x: abs(x - period), reverse=True)
    chosen_pattern = None

    while ordered_patterns:
        patterns = history_patterns.get(ordered_patterns.pop(), None)
        today_period_patterns = patterns.get(day_name,None)
        if today_period_patterns:
            patterns_with_enough_songs = [pattern for pattern in today_period_patterns if len(pattern) > playlist_length]
            if patterns_with_enough_songs:
                chosen_pattern = choose_pattern_with_random_probability(patterns_with_enough_songs)
            else:
                if sum([len(pattern) for pattern in today_period_patterns]) >= playlist_length:
                    chosen_pattern = overlap_patterns(today_period_patterns)
        if chosen_pattern:
            break

    return chosen_pattern
        



def compute_best_history_patterns(history_patterns, day_name):
    best_history_patterns = {}
    for period, patterns in history_patterns.items():
        chosen_pattern = None
        today_period_patterns = patterns.get(day_name, None)
        if today_period_patterns:
            patterns_with_enough_songs = [pattern for pattern in today_period_patterns if len(pattern) > playlist_length]
            if patterns_with_enough_songs:
                chosen_pattern = choose_pattern_with_random_probability(patterns_with_enough_songs)
            else:
                if sum([len(pattern) for pattern in today_period_patterns]) >= playlist_length:
                    chosen_pattern = overlap_patterns(today_period_patterns)
        
        if not today_period_patterns or not chosen_pattern:
            chosen_pattern = compute_closest_pattern(period, history_patterns, day_name)

        if chosen_pattern:
            best_history_patterns[period] = chosen_pattern

    return best_history_patterns

def compute_history_pattern_day_hour(periods, timestamp):
    patterns = []
    current_pattern = []
    
    previous_timestamp = timestamp - timedelta(hours=1)
    tracks = sorted(periods[timestamp], key=lambda x: x['played_at'])

    previous_tracks = periods.get(previous_timestamp, None)
    if previous_tracks:
        previous_tracks = sorted(previous_tracks, key=lambda x: x['played_at'])
        if tracks[0]['played_at'] - previous_tracks[-1]['played_at'] <= timedelta(minutes=15):
            first_track_index = next((i for i, track in enumerate(tracks) if track['played_at'] - tracks[i-1]['played_at'] > timedelta(minutes=15)), None)
            if first_track_index is not None:
                tracks = tracks[first_track_index:]
            else:
                return patterns

    for track in tracks:
        if not current_pattern or track['played_at'] - current_pattern[-1]['played_at'] <= timedelta(minutes=15):
            current_pattern.append(track)
        else:
            patterns.append(current_pattern)
            current_pattern = [track]

    end_of_period = timestamp + timedelta(hours=1)
    last_period_song_timestamp = current_pattern[-1]['played_at'].replace(tzinfo=None)
    while end_of_period - last_period_song_timestamp <= timedelta(minutes=15):
            end_of_period = timestamp + timedelta(hours=1)
            if end_of_period in periods:
                next_tracks = periods[end_of_period]
                next_tracks = sorted(next_tracks, key=lambda x: x['played_at'])
                for next_track in next_tracks:
                    if next_track['played_at'] - current_pattern[-1]['played_at'] > timedelta(minutes=15):
                        break
                    current_pattern.append(next_track)
                    last_period_song_timestamp = current_pattern[-1]['played_at'].replace(tzinfo=None)
                timestamp = end_of_period
            else:
                break
    
    patterns.append(current_pattern)
    return patterns


def compute_listening_history_patterns(periods):
    history_patterns = {}
    sorted_periods = sorted(periods.items(), key=lambda x: x[0], reverse=True)
    for hour in hours:
        history_patterns_days = {}
        for timestamp, tracks in sorted_periods:
            if timestamp.hour == hour:
                day = timestamp.strftime("%A")
                if not history_patterns_days.get(day, None):
                    history_patterns_days[day] = []
                
                history_patterns_days[day].extend(compute_history_pattern_day_hour(periods, timestamp))
        history_patterns[hour] = history_patterns_days

    return history_patterns


def get_features(tracks):
    if tracks[0].get('track', None):
        ids = [track['track']['id'] for track in tracks]
    else:
        ids = [track['id'] for track in tracks]
    features = spotify.audio_features(tracks=ids)
    feature_list = []
    for feature in features:
        if feature:
            track_features = feature.get('id', None)
            if track_features:
                final_features = dict(filter(lambda item: item[0] not in feature_names_to_remove, feature.items()))
                feature_list.append(final_features)

    return feature_list
#Dynamic programming algotithm that computes, for every playlist pattern, the best song ordering
def compute_optimal_solution_indexes(history_patterns, playlist_patterns):
    optimal_solutions_indexes = {}

    for period, playlist in playlist_patterns.items():
        if not history_patterns.get(period, None):
            continue

        history_pattern = get_features(history_patterns[period])
        playlist = get_features(playlist)

        m = len(playlist)
        k = len(history_pattern)

        if  k > m:
            history_pattern = history_pattern[0:m]
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
            limit = playlist_length + n_duplicate_indexes

            playlist = [songs[index]['id'] for index in vertices_period]
            
            for i in range(playlist_length):
                if duplicate_indexes[i]:
                    recommendations = spotify.recommendations(seed_tracks=[playlist[i]], limit=limit).get('tracks')
                    for recommendation in recommendations:
                        if recommendation['id'] not in playlist:
                            playlist[i] = recommendation['id']
                            break

            print(f"Optimal song ordering for period {period}: {playlist}")
            playlists[period] = playlist

    return playlists

#upload the playlists generated for every period on Spotify
def create_playlists(playlists):
    user_id = spotify.current_user()['id']
    for period, track_ids in playlists.items():
        #playlist = spotify.user_playlist_create(user_id, f"Period_{period}", public=False)
        #spotify.playlist_add_items(playlist['id'], track_ids)
        print(f"Uploaded on Spotify the optimal playlist for period {period}")



def main():
    song_sets, periods = retrieve_data() 
    day_name = 'Friday'

    if song_sets and periods:
        history_patterns = compute_listening_history_patterns(periods)
        best_history_patterns = compute_best_history_patterns(history_patterns, day_name)
        if best_history_patterns:
            optimal_solutions_indexes = compute_optimal_solution_indexes(best_history_patterns, song_sets)
            final_playlists = retrieve_optimal_solution_songs(optimal_solutions_indexes, song_sets)
            create_playlists(final_playlists)
        else:
            print(f"No history patterns found for periods {[key for key in song_sets.keys()]} on day {day_name}")
            print(f"You can try changing the variable 'day_name' to another day, or you might want to rerun 'step1.py' with different periods as input")
            print(f"You can also try reducing the value of the global variable 'playlist length'")
    else:
        print("No song sets retrieved")
if __name__ == '__main__':
    main()
