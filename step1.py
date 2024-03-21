from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import davies_bouldin_score
from scipy.spatial.distance import pdist, squareform
from scipy.spatial import distance
import numpy as np
import math
import pickle
from listening_history_manager import recently_played_songs, spotify
from k_means_constrained import KMeansConstrained

feature_names_to_remove = ["uri", "track_href", "analysis_url", "type", "duration_ms"]
playlist_length = 48

days = set()
hours = [i for i in range(0,24)]
period_hours = set()

#Spotify API feature intervals
constraints = {
    'target_danceability': {'min':0, 'max':1},
    'target_energy': {'min':0, 'max':1}, 
    'target_key': {'min':0, 'max':11}, 
    'target_loudness': {'min':float('-inf'), 'max':float('inf')}, 
    'target_mode': {'min':0, 'max':1}, 
    'target_speechiness': {'min':0, 'max':1}, 
    'target_acousticness': {'min':0, 'max':1}, 
    'target_instrumentalness': {'min':0, 'max':1}, 
    'target_liveness': {'min':0, 'max':1}, 
    'target_valence': {'min':0, 'max':1}, 
    'target_tempo': {'min':float('-inf'), 'max':float('inf')},
    'target_time_signature': {'min':0, 'max':5}
}

#NTNA: number of new tracks by new artists played during day 'day', during the period 'hour'
#NTKA: number of new tracks by known artists played during day 'day', during the period 'hour'
def compute_dNTNA_dNTKA(current_period, periods):
    current_period_songs = periods.get(current_period)
    new_song = True
    new_artist = True
    period_dNTNA = 0
    period_dNTKA = 0
    for song in current_period_songs:
        for period, tracks in periods.items():
            if period < current_period:
                for track in tracks:
                    if track['id'] == song['id']:
                        new_song = False
                    
                    if track['artists'][0]['id'] == song['artists'][0]['id']:
                        new_artist = False
        if new_song and new_artist:
            period_dNTNA += 1
        if new_song and not new_artist:
            period_dNTKA += 1

    return period_dNTNA,period_dNTKA


#dictionary that maps a period (datetime) to the list of tracks played in that period
def compute_periods():
    periods = {}
    
    for track_item in recently_played_songs:
        #a period is identified by the day and the hour in which some tracks in the listening history have been played
        timestamp = datetime.strptime(track_item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(minute=0, second=0, microsecond=0)

        day = datetime(timestamp.year, timestamp.month, timestamp.day)
        hour = timestamp.hour

        days.add(day)
        period_hours.add(hour)

        if not periods.get(timestamp, None):
            periods[timestamp] = []
        
        #we are only interested in the 'track' data returned by the Spotify API response
        periods[timestamp].append(track_item['track'])
    
    return periods


#dictionary that maps a period (hour) to a list of features dictionaries, one for every track in that period
def compute_listening_history(periods):
    history = {}
    for period, tracks in periods.items():
        if isinstance(period, datetime):
            hour = period.hour
        else:
            hour = period
        if not history.get(hour,None):
            history[hour] = []
        track_ids = [track['id'] for track in tracks]
        features = spotify.audio_features(tracks=track_ids)
        for feature in features:
            if feature:
                track_features = feature.get('id', None)
                if track_features:
                    final_features = dict(filter(lambda item: item[0] not in feature_names_to_remove, feature.items()))
                    history[hour].append(final_features)

    return history

#pair (NTNA, NTKA) representing the user listening habits for every period in the listening history
#dictionary that maps every period hour present in the listening history to the relative pair (NTNA,NTKA)
def compute_listening_habits(periods): 
    Ph = {}
    for hour in period_hours:
        dNTNA = 0
        dNTKA = 0
        h = 0
        for day in days:
            current_period = datetime(day.year, day.month, day.day, hour)
            if periods.get(current_period, None):
                h += len(periods.get(current_period))
                period_dNTNA, period_dNTKA = compute_dNTNA_dNTKA(current_period, periods)
                dNTNA += period_dNTNA
                dNTKA += period_dNTKA 
        NTNA = 100 * dNTNA / h
        NTKA = 100 * dNTKA / h
        Ph[hour] = (NTNA,NTKA)
    return Ph


#for each period, return the most similar song set among the four generated
def compute_most_similar_song_sets(song_sets, periods, listening_habits): 
    #dictionary that maps a period to a dictionary of listening habits (one for each song set of relative to that period)
    Ph = {}
    for period_song_set, songsets in  song_sets.items():
        #dictionary that maps an identifier (name of the algorithm) to the corrisponding pair (NTNA,NTKA)
        Ph_songsets = {}
        for algorithm_name, tracks_song_set in songsets.items():
            ntna = 0
            ntka = 0
            h = 0
            for track_item_song_set in tracks_song_set:
                h += 1
                track_song_set_id = track_item_song_set['id']
                track_song_set_artist = track_item_song_set['artists'][0]['id']

                history_ids = [track_item_history['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history ]
                history_artists = [track_item_history['artists'][0]['id'] for period_history, tracks_history in periods.items() for track_item_history in tracks_history]

                if track_song_set_id not in history_ids and track_song_set_artist not in history_artists:
                    ntna += 1
                elif track_song_set_id not in history_ids and track_song_set_artist in history_artists:
                    ntka += 1


            Ph_songsets[algorithm_name] = (100*ntna/h,100*ntka/h)

        Ph[period_song_set] = Ph_songsets

    most_similar = {}

    #use the euclidean distance in order to pick, for each period, the generated song set that is most similar to the user listening habits
    for period_song_set, Ph_values in Ph.items():
        euclidean_distances = []
        for algorithm_name, (ntna, ntka) in Ph_values.items():
            euclidean_distance = np.sqrt((ntna - listening_habits[period_song_set][0])**2 + (ntka - listening_habits[period_song_set][1])**2)
            euclidean_distances.append((algorithm_name, euclidean_distance))

        most_similar[period_song_set] = min(euclidean_distances, key=lambda x: x[1])
    
    most_similar_song_set = {}
    for period_song_set, (algorithm_name, _) in most_similar.items():
        most_similar_song_set[period_song_set] = song_sets[period_song_set][algorithm_name]


    return most_similar_song_set


#performs KMeans clustering on a set of feature vectors
def kmeans(features_vector, n_clusters):
    #Extract numerical features from the feature vectors and convert them into a numpy array
    all_features = np.array([[value for value in features.values() if not isinstance(value, str)] for features in features_vector])
    
    #Standardize the features to have mean=0 and variance=1
    scaler = StandardScaler()
    all_features_scaled = scaler.fit_transform(all_features)
    
    # Initialize KMeans clustering algorithm with a specified number of clusters and minimum cluster size
    kmeans = KMeansConstrained(n_clusters=n_clusters, size_min=4)
    kmeans.fit(all_features_scaled)
    
    #Calculate the Davies-Bouldin index as a measure of clustering quality
    davies_bouldin_index = davies_bouldin_score(all_features_scaled, kmeans.labels_)
    
    #Assign each data point to its corresponding cluster
    clusters = [[] for _ in range(n_clusters)]
    for i, label in enumerate(kmeans.labels_):
        clusters[label].append(features_vector[i])
    
    #Inverse transform the centroids to the original feature space
    centroids = scaler.inverse_transform(kmeans.cluster_centers_)
    centroids_dict = [{key: value for key, value in zip(features_vector[0].keys(), centroid)} for centroid in centroids]
    
    #Rename the key 'id' to 'time_signature' for each centroid dictionary
    for centroid in centroids_dict:
        centroid['time_signature'] = centroid.pop('id')

    #Return the clusters, centroids, and Davies-Bouldin index
    return clusters, centroids_dict, davies_bouldin_index

#performs FPF clustering on a set of feature vectors
def furthest_point_first(features_vector, n_clusters, min_size=4):
    # Calculate the total number of samples and the required number of samples for clustering
    num_samples = len(features_vector)
    required_samples = min_size * n_clusters

    # Check if the required number of samples exceeds the total number of samples
    if required_samples > num_samples:
        raise ValueError("The product of min_size and n_clusters is greater than the number of samples.")
    
    #Extract numerical features from the feature vectors and convert them into a numpy array
    all_features = np.array([[value for value in features.values() if not isinstance(value, str)] for features in features_vector])
    
    #Calculate pairwise Euclidean distances between samples
    distances = squareform(pdist(all_features, metric='euclidean'))
    
    #Standardize the features to have mean=0 and variance=1
    scaler = StandardScaler()
    all_features_scaled = scaler.fit_transform(all_features)

    #Initialize with a random point as centroid
    centroids = [np.random.randint(num_samples)]

    #Select additional centroids using the Furthest Point First algorithm
    while len(centroids) < n_clusters:
        max_distances = distances[:, centroids].min(axis=1)
        new_centroid = np.argmax(max_distances)
        if new_centroid not in centroids:
            centroids.append(new_centroid)

    #Assign labels to data points based on the closest centroid
    labels = np.argmin(distances[:, centroids], axis=1)

    #ensure that each cluster has at least min_size points
    while any(np.sum(labels == label) < min_size for label in range(n_clusters)):
        for label in range(n_clusters):
            cluster_indices = np.where(labels == label)[0]
            if len(cluster_indices) < min_size:
                remaining_indices = np.setdiff1d(np.arange(num_samples), centroids)
                max_distances = distances[remaining_indices][:, cluster_indices].min(axis=1)
                new_point_index = remaining_indices[np.argmax(max_distances)]
                centroids.append(new_point_index)
                labels[new_point_index] = label
    #Calculate the Davies-Bouldin index as a measure of clustering quality
    davies_bouldin_index = davies_bouldin_score(all_features_scaled, labels)

    #Assign data points to clusters
    clusters = [[] for _ in range(n_clusters)]
    for i, label in enumerate(labels):
        clusters[label].append(features_vector[i])

    #Inverse transform the centroids to the original feature space
    centroids = scaler.inverse_transform(all_features_scaled[centroids])
    centroids_dict = [{key: value for key, value in zip(features_vector[0].keys(), centroid)} for centroid in centroids]

    #Rename the key 'id' to 'time_signature' for each centroid dictionary
    for centroid in centroids_dict:
        centroid['time_signature'] = centroid.pop('id')

    #Return the clusters, centroids, and Davies-Bouldin index
    return clusters, centroids_dict, davies_bouldin_index

#dictionary that maps a period (datetime) to a pair (K,F) of clusterings
def compute_clusterings(periods_listening_history):
    clusterings = {}
    for period, features in periods_listening_history.items():
        clusterings[period] = {}
        for method in ['kmeans', 'fpf']:
            best_solution = None
            best_davies_bouldin_index = float('inf')
            n_clusters = float('inf')

            for k in range(2, math.floor(math.sqrt(len(features))) + 1):
                try:
                    labels, centroids, davies_bouldin_index = kmeans(features, k) if method == 'kmeans' else furthest_point_first(features, k)
                    if davies_bouldin_index < best_davies_bouldin_index:
                        best_solution = labels
                        best_centroids = centroids
                        best_davies_bouldin_index = davies_bouldin_index
                        n_clusters = k
                except ValueError:
                    continue

            if best_davies_bouldin_index != float('inf'):
                clusterings[period][method] = (best_solution, best_centroids, n_clusters)
                print(f"Generated {method} clustering for period {period}")
            else:
                print(f"Couldn't generate {method} clustering for period {period}")
    return clusterings



#linear heuristic for recommending tracks based on a given cluster and its centroid
def linear_heuristic(cluster, centroid, m, song_set):  
    #Calculate Euclidean distances between each song in the cluster and the centroid
    distances = [distance.euclidean([value for value in song.values() if not isinstance(value,str)], [value for value in centroid.values() if not isinstance(value,str)]) for song in cluster]
    
    #Combine distances with corresponding songs
    points_with_distances = list(zip(distances, cluster))

    #Sort points based on distances
    sorted_points = sorted(points_with_distances, key=lambda x: x[0])

    
    #Define indexes to select representative points from the sorted list
    point_indexes = [0, math.floor(len(cluster)/3), 2*math.floor(len(cluster)/3), len(cluster)-1]

    #Retrieve recommendations for representative points
    recommended_tracks = []
    for i, point in enumerate(sorted_points):
        if i in point_indexes:
            #Modify song data to include target features
            modified_song_data = {'target_' + key: value for key, value in point[1].items() if key != 'id'}
            
            #Get recommendations from Spotify API based on seed track and target features
            #if we set limit to be greater than playlist_length, we ensure that our playlist doesn't have any duplicate songs
            tracks = [point[1]['id']]
            recommendations = spotify.recommendations(seed_tracks=tracks, limit=50, kwargs=modified_song_data).get('tracks')
            #Append recommended tracks to the list
            count = 0
            for track in recommendations:
                if track['id'] not in list(set(song['id'] for song in song_set)):
                    recommended_tracks.append(track)
                    count += 1
                if count == int(m):
                    break
    return recommended_tracks


#spheric heuristic for recommending tracks based on a given cluster and its centroid
def spheric_heuristic(cluster, centroid, m, song_set):
    recommended_tracks = []
    
    #Calculate Euclidean distances between each song in the cluster and the centroid
    distances = [distance.euclidean([value for value in song.values() if not isinstance(value,str)], [value for value in centroid.values() if not isinstance(value,str)]) for song in cluster]
    max_distance = max(distances)
    f = 12

    #Generate random directions in the feature space and recommend tracks
    for _ in range(4):
        direction = np.random.randn(f)
        direction /= np.linalg.norm(direction)
        
        #Generate a random point in the direction of the vector from the centroid
        random_point = {key: centroid[key] + direction[i] * max_distance for i, key in enumerate(centroid) if key != 'id'}
        modified_song_data = {'target_' + key: value for key, value in random_point.items()}
        
        #Clip the values of the random point to ensure they are within the specified constraints
        for key,value in modified_song_data.items():
            if value < constraints[key]['min']:
                modified_song_data[key] = constraints[key]['min']
            elif value > constraints[key]['max']:
                modified_song_data[key] = constraints[key]['max']

        #Find the nearest song to the random point in the feature space
        min_distance = float('inf')
        nearest_song = None
        for song in cluster:
            distance_to_song = distance.euclidean([value for value in song.values() if not isinstance(value,str)], [value for value in modified_song_data.values()])
            if distance_to_song < min_distance:
                min_distance = distance_to_song
                nearest_song = song
        
        #Modify song data to include target features
        modified_song_data = {'target_' + key: value for key, value in nearest_song.items() if key != 'id'}
        
        #Get recommendations from Spotify API based on the nearest song and target features
        #if we set limit to be greater than playlist_length, we ensure that our playlist doesn't have any duplicate songs
        recommendations = spotify.recommendations(seed_tracks=[nearest_song['id']], limit=50, kwargs=modified_song_data).get('tracks')
        
        #Append recommended tracks to the list
        count = 0
        for track in recommendations:
            if track['id'] not in list(set(song['id'] for song in song_set)):
                recommended_tracks.append(track)
                count += 1
            if count == m:
                break

    return recommended_tracks



#use the two heuristics to generate, for each period, four different song sets 
def generate_clustering_song_sets(clusterings):
    song_sets = {}
    for period, clustering in clusterings.items():
        if clustering['kmeans'] and clustering['fpf']:
            K, F = clustering['kmeans'], clustering['fpf']
            kmlh_song_set, kmsh_song_set = [], []
            fpflh_song_set, fpfsh_song_set = [], []

            for cluster_set, song_set, heuristic in [(K, kmlh_song_set, 'l'), (K, kmsh_song_set, 's'), (F, fpflh_song_set, 'l'), (F, fpfsh_song_set, 's')]:
                for i, cluster in enumerate(cluster_set[0]):
                    m = playlist_length / (cluster_set[2] * 4)
                    if heuristic == 'l':
                        song_set.extend(linear_heuristic(cluster, cluster_set[1][i], m, song_set))
                    else:
                        song_set.extend(spheric_heuristic(cluster, cluster_set[1][i], m, song_set))

            song_sets[period] = {'kmlh': kmlh_song_set, 'kmsh': kmsh_song_set, 'fpflh': fpflh_song_set, 'fpfsh': fpfsh_song_set}
    return song_sets

            


def main():
    #compute periods based on the playing timestamp of every song
    periods = compute_periods()
    
    #use the Spotify API to retrieve the audio features of the tracks in the listening history
    #store the listening history (filtered by periods) in a dictionary
    listening_history = compute_listening_history(periods)
    print("Retrieved listening history ")

    with open("listening_history.bin", "wb") as file:
            pickle.dump(listening_history, file)

    #compute the listening habits
    listening_habits = compute_listening_habits(periods)
    print("Computed listening habits ")
    
    #in order to speed up the process (and avoid too much API requests) we only run the clusterings of the current period
    current_period = int(datetime.now().hour)
    periods_to_generate_song_sets = [13]

    #pair (NTNA,NTKA) of the selected periods
    listening_habits_periods = {period:listening_habits.get(period, None) for period in periods_to_generate_song_sets}

    if listening_habits_periods and any(value is not None for value in listening_habits_periods.values()): 
        #listening history of the selected periods
        listening_history_filtered = {period:songs for period, songs in listening_history.items() if period in periods_to_generate_song_sets}
        if listening_history_filtered and any(len(value) != 0 for value in listening_history_filtered.values()):
            #run the clusterings
            clusterings = compute_clusterings(listening_history_filtered)
            if any(clusterings.values()):
                #generate the song sets
                clustering_song_sets = generate_clustering_song_sets(clusterings)
                #among the song sets generated, choose the most similar to the pair (NTNA,NTKA)
                
                most_similar_song_sets = compute_most_similar_song_sets(clustering_song_sets, periods, listening_habits_periods)

                if most_similar_song_sets:
                    #store the playlist
                    for period, song_set in most_similar_song_sets.items():
                        print(f"Best song set for period {period}:")
                        for song in song_set:
                            print(song['name'])
                        print("\n")
                    with open("most_similar_song_set.bin", "wb") as file:
                        pickle.dump(most_similar_song_sets, file)
                        print("Song sets uploaded")
            else:
                 print(f"No valid clusterings produced for periods {periods_to_generate_song_sets}")
        else:
            print(f"No listening history detected for periods {periods_to_generate_song_sets}")
    else:
        print(f"No habits detected for periods {periods_to_generate_song_sets}")

if __name__ == "__main__":
    main()