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

def compute_optimal_solution_indexes(history_patterns, playlist_patterns):
    optimal_solutions_indexes = {}

    for period, playlist in playlist_patterns.items():
        m = len(playlist)

        if not history_patterns[period]:
            break
        
        k = len(history_patterns[period])

        if  k > m:
            history_pattern = history_patterns[period][0:m]
            k = m
        else:
            history_pattern = history_patterns[period]

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

        for i in range(k-2, -1, -1):
            t = vertices_period[0]
            min_index = V[i+1][t]
            if min_index not in vertices_period: #duplicate indexes ?
                vertices_period.insert(0, min_index)
        
        optimal_solutions_indexes[period] = vertices_period
    return optimal_solutions_indexes


def retrieve_optimal_solution_songs(optimal_solutions_indexes, playlist_patterns):
    playlists = {}
    for period, songs in playlist_patterns.items():
        playlist = [songs[index]['id'] for index in optimal_solutions_indexes[period]]
        playlists[period] = playlist
    
    return playlists

def main():
    song_sets, listening_history = retrieve_data() 

    if song_sets and listening_history:
        playlist_patterns = compute_listening_history(song_sets) 
        optimal_solutions_indexes = compute_optimal_solution_indexes(listening_history, playlist_patterns)
        final_playlists = retrieve_optimal_solution_songs(optimal_solutions_indexes, playlist_patterns)
    else:
        print("No song sets retrieved")
if __name__ == '__main__':
    main()