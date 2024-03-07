import pickle
from step1 import compute_listening_history, feature_names_to_remove
from scipy.spatial.distance import euclidean
from listening_history_manager import recently_played_songs, spotify

song_sets_file_path = "most_similar_song_set.bin"
listening_history_file_path = "listening_history.bin"

def retrieve_data():
    song_sets = None
    listening_history = None
    with open(song_sets_file_path, "rb") as file:
        song_sets = pickle.load(file)

    with open(listening_history_file_path, "rb") as file:
        listening_history = pickle.load(file)

    return song_sets, listening_history

def compute_optimal_solution(history_pattern, playlist_patterns, k):
    optimal_solutions = {}

    for period, playlist in playlist_patterns.items():
        M = []
        V = []
        m = len(playlist)

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

        for i in range(k-2, -1, -1):
            t = vertices_period[0]
            min_index = V[i+1][t]
            vertices_period.insert(0, min_index)
        
        optimal_solutions[period] = vertices_period
    return optimal_solutions


def main():
    song_sets, listening_history = retrieve_data() 

    if song_sets and listening_history:
        playlist_patterns = compute_listening_history(song_sets) 
        m = min([len(tracks) for period,tracks in playlist_patterns.items()])
        listening_history = [track_item['track']['id'] for track_item in recently_played_songs]
        history_pattern_features = list(filter(None, spotify.audio_features(tracks=listening_history)))[0:m]
        history_pattern = [{key:value for key,value in song.items() if key not in feature_names_to_remove} for song in history_pattern_features]
        optimal_solutions = compute_optimal_solution(history_pattern, playlist_patterns, len(history_pattern))
        
        print(optimal_solutions)
    else:
        print("No song sets retrieved")
if __name__ == '__main__':
    main()