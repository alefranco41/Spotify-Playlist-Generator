#general purpose modules
from datetime import datetime #manage timestamps of songs
import math
import pickle
from listening_history_manager import compute_recently_played_songs, change_credentials, get_features, get_tracks, get_recommendations
import os
#modules for clustering
from sklearn.preprocessing import StandardScaler 
from sklearn.metrics import davies_bouldin_score
from scipy.spatial.distance import pdist, squareform
from scipy.spatial import distance
from k_means_constrained import KMeansConstrained #K-means clustering with constraints to impose a minimum number of points for each cluster
import numpy as np

#global variables
playlist_length = 48 #length of the song sets, needed to compute how many recommendations each cluster point has to generate
listening_history_suffix = "_listening_history.bin"
most_similar_song_sets_suffix = "_most_similar_song_sets.bin"
periods_suffix = "_periods.bin"
listening_habits_suffix = "_listening_habits.bin"
file_names_to_keep = ["recently_played_songs.bin", "playlists.bin", "results.bin"]
data_directory = "data"
#in order to speed up the process (and avoid too much API requests) we only run the clusterings of the current period
input_message = """If you own the file "StreamingHistory.json" obtained through Spotify's "Request data" feature, insert its path here, press ENTER otherwise: """
#Spotify API intervals for audio features, needed for the song-set generation with spheric heuristic
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


def compute_prefix_name(listening_history_file):
    if not listening_history_file:
        return "normal_mode"
    file_name = os.path.basename(listening_history_file)
    file_name_without_extension = os.path.splitext(file_name)[0]
    file_name_without_underscore = file_name_without_extension.replace("_", "")
    return file_name_without_underscore

#check if the module 'step1' is running with a "StreamingHistory.json" file provided by the user or not.
#this check is needed because the structure of the dictionary 'periods' will be different. 
def check_listening_history_file(periods):
    ret = None
    try:
        if list(periods.values())[0][0].get('endTime', None):
            ret = True
    except IndexError:
        ret = False

    return ret


#dNTNA: number of new tracks by new artists played in a given period
#dNTKA: number of new tracks by known artists played in a given period
def compute_dNTNA_dNTKA(current_period, periods, current_period_songs, listening_history_file):
    new_song = True
    new_artist = True
    period_dNTNA = 0
    period_dNTKA = 0
    periods_items = periods.items()

    for song in current_period_songs:
        for period, tracks in periods_items:
            if period < current_period:
                for track in tracks:
                    if listening_history_file:
                        try:
                            track_id = track['TrackID']
                            track_artist_id = track['artistName']
                            current_period_track_id = song['TrackID']
                            current_period_track_artist_id = song['artistName']
                        except KeyError:
                            track_id = track['id']
                            track_artist_id = track['artists'][0]['id']
                            current_period_track_id = song['id']
                            current_period_track_artist_id = song['artists'][0]['id']
                    else:
                        track_id = track['track']['id']
                        track_artist_id = track['track']['artists'][0]['id']
                        current_period_track_id = song['track']['id']
                        current_period_track_artist_id = song['track']['artists'][0]['id']   

                    if track_id == current_period_track_id:
                        new_song = False
                    if track_artist_id == current_period_track_artist_id:
                            new_artist = False
        if new_song and new_artist:
            period_dNTNA += 1
        if new_song and not new_artist:
            period_dNTKA += 1

    return period_dNTNA,period_dNTKA


#dictionary that maps a period to the list of tracks played in that period
#a period is identified by the day (year/month/day) and the hour in which some tracks in the listening history have been played
def compute_periods(listening_history_file_data, prefix_name):
    periods = {}
    periods_file_path = os.path.join(data_directory, prefix_name + periods_suffix)

    spotify = change_credentials()

    if listening_history_file_data:
        try:
            if os.path.exists(periods_file_path):
                with open(periods_file_path, "rb") as file:
                    periods = pickle.load(file)
                    print(f"Retrieved periods from {periods_file_path}")
                    return periods
        except Exception as e:
            print(e)
            pass
        songs = listening_history_file_data
        if not songs[0].get('artistName', None):
            timestamps = [song['endTime'] for song in songs]
            songs = get_tracks(songs, timestamps, spotify)
    else:
        songs = compute_recently_played_songs(spotify)
    
    
    for track_item in songs:
        if listening_history_file_data:
            timestamp = track_item['endTime']
        else:
            timestamp = track_item['played_at']

        
        timestamp = timestamp.replace(minute=0, second=0, microsecond=0).replace(tzinfo=None)
        if not periods.get(timestamp, None):
            periods[timestamp] = []
        
        periods[timestamp].append(track_item)
    
    
    if not periods:
        print("Couldn't retrieve or compute periods")
    else:
        with open(periods_file_path, "wb") as file:
            pickle.dump(periods, file)
        print("Computed periods")
    
    return periods

#compute the track ids needed to get the audio features through the Spotify API
def compute_track_ids(period, tracks):
    listening_history_file = False
    if tracks[0].get('TrackID', None):
        listening_history_file = True

    if listening_history_file:
        track_ids = [track['TrackID'] for track in tracks]
    else:
        if isinstance(period, datetime):
            try:
                track_ids = [track['track']['id'] for track in tracks]
            except KeyError:
                track_ids = [track['id'] for track in tracks]
        else: 
            track_ids = [track['id'] for track in tracks]        

    return track_ids

#dictionary that maps a period (hour) to a list of (filtered) features dictionaries, one for every track in that period
def compute_listening_history(periods, prefix_name):
    listening_history = {}
    listening_history_file_path = os.path.join(data_directory, prefix_name + listening_history_suffix)

    spotify = change_credentials()
    
    try:
        if os.path.exists(listening_history_file_path):
            with open(listening_history_file_path, "rb") as file:
                listening_history = pickle.load(file)
                print(f"Retrieved listening history from {listening_history_file_path}")
                return listening_history
    except Exception as e:
        print(e)
        pass
        
    for i, (period, tracks) in enumerate(periods.items()):
        print(f"Computing listening history for period #{i+1}/{len(periods)}")
        if isinstance(period, datetime):
            hour = period.hour
            day = period.strftime("%A")

        if not listening_history.get((day,hour),None):
            listening_history[(day,hour)] = []
        
        track_ids = compute_track_ids(period, tracks)
        
        
        while True:
            try:
                features = get_features(track_ids,spotify)
            except Exception as e:
                print(e)
                spotify = change_credentials()
            else:
                break

        listening_history[(day,hour)].extend(features)


    if not listening_history:
        print("Couldn't compute or retrieve the listening history")
        #sys.exit()
    else:
        with open(listening_history_file_path, "wb") as file:
                pickle.dump(listening_history, file)
        print("Computed listening history ")

    
    return listening_history

#pair (NTNA, NTKA) representing the user listening habits for every period in the listening history
#dictionary that maps every period hour present in the listening history to the relative pair (NTNA,NTKA)
def compute_listening_habits(periods, prefix_name): 
    Ph = {}
    listening_history_file = check_listening_history_file(periods)
    listening_habits_file_path = os.path.join(data_directory, prefix_name + listening_habits_suffix)
    try:
        if os.path.exists(listening_habits_file_path):
            with open(listening_habits_file_path, "rb") as file:
                Ph = pickle.load(file)
                print(f"Retrieved listening habits from {listening_habits_file_path}")
                return Ph
    except Exception as e:
        print(e)
        pass
        
    
    days = list(set([datetime(day.year, day.month, day.day) for day in periods.keys()]))
    hours = [i for i in range(0,24)]
    total = len(days) * len(hours)
    count = 1
    print(f"Computing listening habits:")
    for hour in hours:
        dNTNA = 0
        dNTKA = 0
        h = 0
        for day in days:
            print(f"Progress: {round(100*count/total, 2)}%")
            count += 1
            current_period = datetime(day.year, day.month, day.day, hour)
            current_period_songs = periods.get(current_period, None)
            if current_period_songs:
                h += len(current_period_songs)
                period_dNTNA, period_dNTKA = compute_dNTNA_dNTKA(current_period, periods, current_period_songs, listening_history_file)
                dNTNA += period_dNTNA
                dNTKA += period_dNTKA 
        if h > 0:
            NTNA = 100 * dNTNA / h
            NTKA = 100 * dNTKA / h
            Ph[hour] = (NTNA,NTKA)

    if not Ph:
        print("Couldn't compute or retrieve the listening habits")
        #sys.exit()
    else:
        with open(listening_habits_file_path, "wb") as file:
                pickle.dump(Ph, file)
        print("Computed listening habits ")

    return Ph

def retrieve_most_similar_song_set(prefix_name, day, hour):
    most_similar_song_sets_file_path = os.path.join(data_directory, prefix_name + most_similar_song_sets_suffix)
    most_similar_song_sets = {}
    try:
        if os.path.exists(most_similar_song_sets_file_path):
            with open(most_similar_song_sets_file_path, "rb") as file:
                most_similar_song_sets = pickle.load(file)
    except (FileNotFoundError, EOFError):
        pass
    
    if most_similar_song_sets.get((day,hour), None):
        return {(day,hour):most_similar_song_sets[(day,hour)]}
    
    return None


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
                if track_song_set_id not in history_ids and track_song_set_artist not in history_artists:
                    ntna += 1
                elif track_song_set_id not in history_ids and track_song_set_artist in history_artists:
                    ntka += 1


            Ph_songsets[algorithm_name] = (100*ntna/h,100*ntka/h)

        Ph[period_song_set] = Ph_songsets
    
    print(Ph)

    most_similar = {}

    #use the euclidean distance in order to pick, for each period, the generated song set that is most similar to the user listening habits
    for period_song_set, Ph_values in Ph.items():
        euclidean_distances = []
        for algorithm_name, (ntna, ntka) in Ph_values.items():
            euclidean_distance = np.sqrt((ntna - listening_habits[period_song_set[1]][0])**2 + (ntka - listening_habits[period_song_set[1]][1])**2)
            euclidean_distances.append((algorithm_name, euclidean_distance))

        most_similar[period_song_set] = min(euclidean_distances, key=lambda x: x[1])
    
    most_similar_song_set = {}
    for period_song_set, (algorithm_name, _) in most_similar.items():
        most_similar_song_set[period_song_set] = song_sets[period_song_set][algorithm_name]
    
    if not most_similar_song_set:
        print(f"Couldn't compute most similar song-set for periods {[item[0] for item in list(most_similar.items())]}")
        #sys.exit(2)
    
    print(f"Computed most similar song-set for periods {[item[0] for item in list(most_similar.items())]}")
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
    
    if not clusterings:
        print(f"Couldn't compute clusterings for periods {list(periods_listening_history.keys())}")
        #sys.exit(2)
    
    return clusterings



#linear heuristic for recommending tracks based on a given cluster and its centroid
def linear_heuristic(cluster, centroid, m, song_set, spotify):  
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
    #with open("stats.txt", "a") as file:
    for i, point in enumerate(sorted_points):
        if i in point_indexes:
            #Modify song data to include target features
            modified_song_data = {'target_' + key: value for key, value in point[1].items() if key != 'id'}
            #file.write(f"Recommendations for song {point[1]['id']} (linear heuristic):\n")
            #Get recommendations from Spotify API based on seed track and target features
            #if we set limit to be greater than playlist_length, we ensure that our playlist doesn't have any duplicate songs
            tracks = [point[1]['id']]
            print(f"Getting recommendations with linear heuristic for track '{tracks[0]}' of point #{i}...")
            
            while True:
                try:
                    recommendations = get_recommendations(spotify=spotify, seed_tracks=tracks, limit=100, kwargs=modified_song_data).get('tracks')
                except Exception as e:
                    print(e)
                    spotify = change_credentials()
                else:
                    break
            #Append recommended tracks to the list
            count = 0
            for track in recommendations:
                if track['id'] not in list(set(song['id'] for song in song_set)):
                    recommended_tracks.append(track)
                    #file.write(f"{track['id']}\n")
                    count += 1
                if count == int(m):
                    break
                
    return recommended_tracks

def spheric_heuristic(cluster, centroid, m, song_set, spotify):
    recommended_tracks = []
    constraints_list = list(constraints.keys())

    distances = [distance.euclidean([value for value in song.values() if not isinstance(value,str)], [value for value in centroid.values() if not isinstance(value,str)]) for song in cluster]
    radius = max(distances)
    center = [centroid[key] for key in centroid.keys() if not isinstance(centroid[key], str)]
    
    random_points = []
    unique_songs = len(list(set(track['id'] for track in cluster)))
    if  unique_songs >= 4:
        limit = 4
    else:
        limit = unique_songs

    while len(random_points) < limit:
        # Generate a single random point in the hypersphere
        randomnessGenerator = np.random.default_rng()
        X = randomnessGenerator.normal(size=len(center))
        U = randomnessGenerator.random()
        random_point = radius * (U**(1/len(center))) / np.sqrt(np.sum(X**2)) * X
        random_point += np.array(center)  # Translate point to center
        
        # Generate modified song data from the random point
        modified_song_data = {}
        for j, value in enumerate(random_point):
            key = constraints_list[j]
            modified_song_data[key] = value
        
        # Clip the values of the random point to ensure they are within the specified constraints
        for key, value in modified_song_data.items():
            if value < constraints[key]['min']:
                modified_song_data[key] = constraints[key]['min']
            elif value > constraints[key]['max']:
                modified_song_data[key] = constraints[key]['max']
        
        # Find the nearest song to the random point in the feature space
        min_distance = float('inf')
        nearest_song = None
        for song in cluster:
            distance_to_song = distance.euclidean([value for value in song.values() if not isinstance(value,str)], [value for value in modified_song_data.values()])
            if distance_to_song < min_distance:
                min_distance = distance_to_song
                nearest_song = song
        
        # Check if the nearest song is different from previously selected nearest songs
        if nearest_song not in random_points:
            random_points.append(nearest_song)
            
    # Generate recommendations for each nearest song
    #with open("stats.txt", "a") as file:
    for i, nearest_song in enumerate(random_points):
        #Modify song data to include target features
        modified_song_data = {'target_' + key: value for key, value in nearest_song.items() if key != 'id'}
            
        #Get recommendations from Spotify API based on the nearest song and target features
        #if we set limit to be greater than playlist_length, we ensure that our playlist doesn't have any duplicate songs
        print(f"Getting recommendations for track '{nearest_song['id']}' with spheric heuristic for point #{i}...")
        #file.write(f"Recommendations for song {nearest_song['id']} (spheric heuristic): \n")
        
        while True:
            try:
                recommendations = get_recommendations(spotify=spotify, seed_tracks=[nearest_song['id']], limit=100, kwargs=modified_song_data).get('tracks')
            except Exception as e:
                print(e)
                spotify = change_credentials()
            else:
                break

            
        #Append recommended tracks to the list
        count = 0
        for track in recommendations:
            if track['id'] not in list(set(song['id'] for song in song_set)):
                recommended_tracks.append(track)
                #file.write(f"{track['id']} \n")
                count += 1
            if count == m:
                break
        
    return recommended_tracks


#use the two heuristics to generate, for each period, four different song sets 
def generate_clustering_song_sets(clusterings):
    song_sets = {}
    for period, clustering in clusterings.items():
        clustering_kmeans = clustering.get('kmeans', None)
        clustering_fpf = clustering.get('fpf', None)

        if clustering_kmeans and clustering_fpf:
            K, F = clustering_kmeans, clustering_fpf
            kmlh_song_set, kmsh_song_set = [], []
            fpflh_song_set, fpfsh_song_set = [], []
            n = 1
            for cluster_set, song_set, heuristic in [(K, kmlh_song_set, 'l'), (K, kmsh_song_set, 's'), (F, fpflh_song_set, 'l'), (F, fpfsh_song_set, 's')]: 
                spotify = change_credentials()
                
                m = playlist_length / (cluster_set[2] * 4)
                if int(m) != m:
                    m = math.ceil(m)

                for i, cluster in enumerate(cluster_set[0]):
                    print(f"m = {m}, number of clusters: {cluster_set[2]}")
                    #with open("stats.txt", "a") as file:
                        #file.write(f"Generating song set #{n} for period {period}... \n")
                    print(f"Generating song set #{n} for period {period}...")
                    if heuristic == 'l':
                        song_set.extend(linear_heuristic(cluster, cluster_set[1][i], m, song_set, spotify))
                    else:
                        song_set.extend(spheric_heuristic(cluster, cluster_set[1][i], m, song_set, spotify))
                print(f"Generated song set #{n} for period {period}")
                n += 1
            song_sets[period] = {'kmlh': kmlh_song_set, 'kmsh': kmsh_song_set, 'fpflh': fpflh_song_set, 'fpfsh': fpfsh_song_set}
    if not song_sets:
        print(f"Couldn't generate song-sets for periods {list(clustering.keys())}")
    return song_sets

def upload_most_similar_song_sets(most_similar_song_sets, prefix_name):
    #with open("stats.txt", "a") as file:                   
    for period, song_set in most_similar_song_sets.items():
        print(f"Best song set for period {period}:")
        #file.write(f"Best song set for period {period}: \n")
        for song in song_set:
            print(song['name'])
            #file.write(f"{song['id']} \n")
        print("\n")
    
    most_similar_song_sets_file_path = os.path.join(data_directory, prefix_name + most_similar_song_sets_suffix)
    
    already_stored_song_sets = {}
    try:
        if os.path.exists(most_similar_song_sets_file_path):
            with open(most_similar_song_sets_file_path, "rb") as file:
                already_stored_song_sets = pickle.load(file)
    except Exception as e:
        print(e)
        pass

    already_stored_song_sets.update(most_similar_song_sets)
    
    with open(most_similar_song_sets_file_path, "wb") as file:
        pickle.dump(already_stored_song_sets, file)

    print("Song sets uploaded")      
