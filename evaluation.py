import pickle
from scipy.spatial.distance import euclidean
import pandas as pd


def retrieve_playlists():
    playlists = {}
    with open("data/playlists.bin", "rb") as file:
        try:
            while True:
                playlists.update(pickle.load(file))
        except EOFError:
            pass

    return playlists

def retrieve_results():
    results = {}
    try:
        with open("data/results.bin", "rb") as file:
            results = pickle.load(file)
    except FileNotFoundError:
        pass

    return results

def compute_vertex_distance(generated_playlist_features, history_pattern_features):
    sum = 0
    for i in range(len(generated_playlist_features) - 1):
        generated_playlist_current_track_features = [feature for feature in generated_playlist_features[i].values() if not isinstance(feature, str)]
        generated_playlist_next_track_features = [feature for feature in generated_playlist_features[i+1].values() if not isinstance(feature, str)]

        euclidean_distance_1 = euclidean(generated_playlist_current_track_features, generated_playlist_next_track_features)
        
        history_pattern_current_track_features = [feature for feature in history_pattern_features[i].values() if not isinstance(feature, str)]
        history_pattern_next_track_features = [feature for feature in history_pattern_features[i+1].values() if not isinstance(feature, str)]

        euclidean_distance_2 = euclidean(history_pattern_current_track_features, history_pattern_next_track_features)
        
        sum += abs(euclidean_distance_1 - euclidean_distance_2)
    return sum


def compute_segment_distance(generated_playlist_features, history_pattern_features):
    sum = 0
    for i in range(len(generated_playlist_features)):
        generated_playlist_track_features = [feature for feature in generated_playlist_features[i].values() if not isinstance(feature, str)]
        history_pattern_track_features = [feature for feature in history_pattern_features[i].values() if not isinstance(feature, str)]
        sum += euclidean(generated_playlist_track_features,history_pattern_track_features)
    return sum
    

def compute_playlist_pattern_distances(playlists, existing_results):
    from step2 import get_features
    results = {}
    print("Results for the new generated playlists:\n")
    i = 1
    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        if len(generated_playlist) == len(history_pattern):
            generated_playlist_features = get_features(generated_playlist)
            history_pattern_features = get_features(history_pattern)
            vertex_distance = compute_vertex_distance(generated_playlist_features, history_pattern_features)
            segment_distance = compute_segment_distance(generated_playlist_features, history_pattern_features)
            pattern_distance = vertex_distance + segment_distance
            results[playlist_data] = (pattern_distance,len(generated_playlist))
            print(f"Result #{i}:\nListening history: {playlist_data[0]}\nDay: {playlist_data[1]}\nHour: {playlist_data[2]}\nMethod: {playlist_data[3]}\nPD: {pattern_distance}\n")
            i += 1
        else:
            results[playlist_data] = None
    
    existing_results.update(results)
    with open("data/results.bin", "wb") as file:
        pickle.dump(existing_results,file)
    
    print("The new generated playlists have been uploaded on 'data/results.bin'")

def generate_spreadsheet(results):
    data = []
    for key, value in results.items():
        LH_filename, day, hour, method = key
        if value:
            df = data.append({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': value[1], 'Pattern_Distance': value[0]})
    
    df = pd.DataFrame(data)
    df.to_excel("playlists_results.xlsx", index=False)
    print("Spreadsheet generated: playlist_results.xlsx")

def main():
    playlists = retrieve_playlists()
    results = retrieve_results()
    if results:
        playlists = {key: playlists[key] for key in playlists if key not in results}
    
    if playlists:
        compute_playlist_pattern_distances(playlists, results)
    else:
        print("No new generated playlists found")

    results = retrieve_results()
    generate_spreadsheet(results)
if __name__ == "__main__":
    main()