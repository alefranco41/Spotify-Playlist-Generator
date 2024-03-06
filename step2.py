import pickle
from step1 import compute_listening_history
from scipy.spatial.distance import euclidean


song_sets_file_path = "most_similar_song_set.bin"
listening_history_file_path = "listening_history.bin"

def retrieve_data(song_sets_file_path, listening_history_file_path):
    song_sets = None
    listening_history = None
    with open(song_sets_file_path, "rb") as file:
        song_sets = pickle.load(file)

    with open(listening_history_file_path, "rb") as file:
        listening_history = pickle.load(file)

    return song_sets, listening_history

def compute_history_pattern(listening_history, m):
    history_pattern = []
    k = 0
    for period, tracks in listening_history.items():
        for track in tracks:
            history_pattern.append(track)
            k += 1
            if k == m:
                return history_pattern
            
    return history_pattern


def compute_optimal_subproblem_solution_matrices(history_pattern, playlist_patterns, k):
    optimal_subproblem_solution_matrices = {}
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
                min_distance = float('inf')
                min_index = -1
                for t in range(m):
                    d1 = euclidean([value for value in history_pattern[i-1].values() if not isinstance(value, str)], [value for value in history_pattern[i].values() if not isinstance(value, str)])
                    d2 = euclidean([value for value in playlist[t].values() if not isinstance(value, str)], [value for value in playlist[j].values() if not isinstance(value, str)])
                    playlist_pattern_distance = M[i-1][t] + abs((d1 - d2))

                    if playlist_pattern_distance < min_distance:
                        min_distance = playlist_pattern_distance
                        min_index = t


                M_i_th_row.append(distance + min_distance)
                V_i_th_row.append(min_index)
                    
            M.append(M_i_th_row)
            V.append(V_i_th_row)

        optimal_subproblem_solution_matrices[period] = (M,V)
    
    return optimal_subproblem_solution_matrices


def retrieve_optimal_solution_vertices(optimal_subproblem_solution_matrices):
    optimal_solutions = {}
    for period, matrices in optimal_subproblem_solution_matrices.items():
        M = matrices[0]
        V = matrices[1]
        
        k = len(M)
        m = len(M[0])

        min_col_index = -1
        min = float("inf")
        for j in range(m):
            if M[k-1][j] < min:
                min = M[k-1][j]
                min_col_index = j

        vertices_period = []

        for i in range(k-1, -1, -1):
            if i == k-1:
                vertices_period.append(min_col_index)
            else:
                t = vertices_period[-1]
                r = V[i+1][t]
                vertices_period.append(r)

        vertices_period.reverse()
        optimal_solutions[period] = vertices_period

    return optimal_solutions


def main():
    song_sets, listening_history = retrieve_data(song_sets_file_path, listening_history_file_path) 

    if song_sets and listening_history:
        playlist_patterns = compute_listening_history(song_sets) 

        for period, song_set in playlist_patterns.items():
            print(len(list(set([song['id'] for song in song_set]))))
        m = min([len(tracks) for period,tracks in playlist_patterns.items()])
        history_pattern = compute_history_pattern(listening_history, m)
        
        optimal_subproblem_solution_matrices = compute_optimal_subproblem_solution_matrices(history_pattern, playlist_patterns, len(history_pattern))
        optimal_subproblem_solution_matrices = compute_optimal_subproblem_solution_matrices(history_pattern, playlist_patterns, len(history_pattern))
        optimal_solutions = retrieve_optimal_solution_vertices(optimal_subproblem_solution_matrices)
        print(optimal_solutions)
    else:
        print("No song sets retrieved")
if __name__ == '__main__':
    main()