from step2 import get_features
import pickle
from scipy.spatial.distance import euclidean


def retrieve_playlists():
    playlists = {}
    with open("playlists.bin", "rb") as file:
        try:
            while True:
                playlists.update(pickle.load(file))
        except EOFError:
            pass

    return playlists

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
    

def compute_playlist_pattern_distances(playlists):
    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        generated_playlist_features = get_features(generated_playlist)
        history_pattern_features = get_features(history_pattern)
        if len(history_pattern_features) == len(generated_playlist_features):
            vertex_distance = compute_vertex_distance(generated_playlist_features, history_pattern_features)
            segment_distance = compute_segment_distance(generated_playlist_features, history_pattern_features)
            pattern_distance = vertex_distance + segment_distance
            print(playlist_data[3], pattern_distance)

def main():
    playlists = retrieve_playlists()
    compute_playlist_pattern_distances(playlists)

if __name__ == "__main__":
    main()