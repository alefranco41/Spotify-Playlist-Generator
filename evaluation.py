import pickle
from scipy.spatial.distance import euclidean
import pandas as pd
import matplotlib.pyplot as plt
from spotipy import SpotifyException
from step1 import compute_periods, compute_listening_history, compute_prefix_name, compute_listening_habits
from step2 import compute_listening_history_patterns, get_features
from listening_history_manager import csv_to_dict, change_credentials
import os
import seaborn as sns

directory_name = "listening_histories"


def print_pattern(pattern):
    for song in pattern:
        print(f"Name: {song['trackName']}, Timestamp: {song['endTime']}")
    print("\n")

def print_listening_history_patterns(listening_history_file, spotify):
    listening_history_file_path = os.path.join(directory_name, listening_history_file)
    listening_history_file_data = csv_to_dict(listening_history_file_path)
    if listening_history_file_data:
        prefix_name = compute_prefix_name(listening_history_file)
        periods = compute_periods(listening_history_file_data, prefix_name, spotify)
        listening_history_patterns = compute_listening_history_patterns(periods, "endTime")
        
    for hour, days_dict in listening_history_patterns.items():
        for day_name, patterns in days_dict.items():
            print(f"Listening history patterns for Day {day_name} and Hour {hour}:")
            for pattern in patterns:
                print(f"Pattern #{patterns.index(pattern)+1}:")
                print_pattern(pattern)
            print("--------------------------------------------------------")




def compute_longest_history_pattern(listening_history_patterns):
    longest_pattern = []
    longest_pattern_day = None
    longest_pattern_hour = None

    for hour, days_dict in listening_history_patterns.items():
        for day_name, patterns in days_dict.items():
            for pattern in patterns:
                if len(pattern) > len(longest_pattern):
                    longest_pattern = pattern
                    longest_pattern_hour = hour
                    longest_pattern_day = day_name
    
    return (longest_pattern_day,longest_pattern_hour,longest_pattern)


def compute_all_data(spotify):
    all_patterns = []
    for listening_history_file in os.listdir(directory_name):
        listening_history_file_path = os.path.join(directory_name, listening_history_file)
        listening_history_file_data = csv_to_dict(listening_history_file_path)
        if listening_history_file_data:
            prefix_name = compute_prefix_name(listening_history_file)
            periods = compute_periods(listening_history_file_data, prefix_name, spotify)
            listening_history = compute_listening_history(periods, prefix_name, spotify)
            listening_history_patterns = compute_listening_history_patterns(periods, "endTime")
            listening_habits = compute_listening_habits(periods, prefix_name)
            all_patterns.append((listening_history_patterns, prefix_name))
    
    pattern_items = []
    for listening_history_patterns, prefix_name in all_patterns:
        for hour, days_patterns in listening_history_patterns.items():
            for day, patterns in days_patterns.items():
                for pattern in patterns:
                    pattern_item = (day,hour,prefix_name,pattern)
                    pattern_items.append(pattern_item)
    
    sorted_patterns = sorted(pattern_items, key=lambda x: len(x[3]), reverse=True)
    with open("data/longest_patterns.txt", "w") as file:
        for pattern in sorted_patterns:
            file.write(f"Listening history file: {pattern[2]}\n")
            file.write(f"Longest pattern length: {len(pattern[3])}\n")
            file.write(f"Day: {pattern[0]}\n")
            file.write(f"Hour: {pattern[1]}\n")
            for song in pattern[3]:
                try:
                    track_name = song['trackName']
                except KeyError:
                    try:
                        track_name = song['track_name']
                    except KeyError:
                        track_name = song['name']
                    
                    file.write(f"TrackName: {track_name} Timestamp: {song['endTime']}\n")
            file.write("\n")


def plot_data(title, data_dict, xlabel="", ylabel="", rotation=None, name="graph.png", total_songs=None, y_limit=None):
    plt.figure(figsize=(15, 6))
    plt.bar(data_dict.keys(), data_dict.values())
    if total_songs:
        plt.title(f"{title} (Total Songs: {total_songs})")
    else:
        plt.title(f"{title}")

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    if y_limit:
        plt.ylim(0, y_limit)
    if rotation:
        plt.xticks(rotation=rotation)
    plt.xticks(range(24))
    plt.savefig(name)

def compute_listening_history_data(spotify):
    average_pattern_lengths = {}
    for file_path in os.listdir("data"):
        prefix_name = file_path.split('_')[0]
        file_path = os.path.join("data", file_path)
        if file_path.endswith("listening_history.bin"):
            with open(file_path, "rb") as file:
                listening_history = pickle.load(file)
                            
            total_songs = 0
            songs_hour = {}
            for hour, songs in listening_history.items():
                total_songs += len(songs)
                songs_hour[hour] = len(songs)
            
            incidence = {}
            for hour, total in songs_hour.items():
                incidence[hour] = round((100 * total / total_songs),2)
            
            periods = compute_periods([], prefix_name, spotify)
            listening_history_patterns = compute_listening_history_patterns(periods, "endTime")


            n_patterns = 0
            total_length = 0
            longest_pattern_length = 0
            longest_pattern_hour = {}
            average_pattern_length_hour = {}
            for hour, days_patterns in listening_history_patterns.items():
                longest_pattern_hour_length = 0
                total_length_hour = 0
                n_patterns_hour = 0
                for day, patterns in days_patterns.items():
                    for pattern in patterns:
                        n_patterns += 1
                        n_patterns_hour += 1
                        total_length += len(pattern)
                        total_length_hour += len(pattern)

                        if len(pattern) > longest_pattern_length:
                            longest_pattern_length = len(pattern)
                        if len(pattern) > longest_pattern_hour_length:
                            longest_pattern_hour_length = len(pattern)
                longest_pattern_hour[hour] = longest_pattern_hour_length
                if n_patterns_hour == 0:
                    average_pattern_length_hour[hour] = 0
                else:
                    average_pattern_length_hour[hour] = total_length_hour / n_patterns_hour
            average_pattern_length = total_length / n_patterns
            average_pattern_lengths[prefix_name] = average_pattern_length
            

            # Plotting data
            plot_data("Song Incidence by Hour", incidence, xlabel="Hour", ylabel="Incidence (%)", name=f"graphs/song_incidences/song_incidence_{prefix_name}.png", total_songs=total_songs, y_limit=25)
            plot_data("Longest Pattern Length by Hour", longest_pattern_hour, xlabel="Hour", ylabel="Length", name=f"graphs/longest_patterns/longest_pattern{prefix_name}.png", y_limit=125)
            plot_data("Average Pattern Length by Hour", average_pattern_length_hour, xlabel="Hour", ylabel="Average Length", name=f"graphs/average_pattern_lengths/average_pattern_lengths_{prefix_name}.png")
    sorted_data = dict(sorted(average_pattern_lengths.items(), key=lambda x: int(x[0][2:])))
    print(sorted_data)
    plot_data("Average Pattern Lengths", sorted_data, xlabel="Listening History", ylabel="Average pattern length", name=f"graphs/average_pattern_lengths.png")

def retrieve_playlists():
    playlists = {}
    try:
        with open("data/playlists.bin", "rb") as file:
            try:
                while True:
                    playlists.update(pickle.load(file))
            except (EOFError):
                pass
    except FileNotFoundError:
        pass

    return playlists

def retrieve_results():
    results = {}
    if os.path.exists("data/results.bin"):
        with open("data/results.bin", "rb") as file:
            try:
                while True:
                    result = pickle.load(file)
                    results.update(result)
            except EOFError:
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
    
def compute_pattern_distance(generated_playlist, history_pattern, spotify):
    generated_playlist_features = get_features(generated_playlist, spotify)
    history_pattern_features = get_features(history_pattern, spotify)
    vertex_distance = compute_vertex_distance(generated_playlist_features, history_pattern_features)
    segment_distance = compute_segment_distance(generated_playlist_features, history_pattern_features)
    
    return vertex_distance + segment_distance


def compute_playlist_pattern_distances(playlists):
    existing_results = retrieve_results()

    print("Results for the generated playlists:\n")
    i = len(existing_results) + 1  # Start counting from the next index


    spotify = change_credentials()

    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        if playlist_data in existing_results:
            continue  # Skip if already computed

        while True:
            pattern_distance = None
            try:
                if len(generated_playlist) == len(history_pattern):
                    pattern_distance = compute_pattern_distance(generated_playlist, history_pattern, spotify)
                else:
                    excess = len(history_pattern) - len(generated_playlist)
                    start_index = excess // 2
                    end_index = start_index + len(history_pattern)
                    history_pattern = history_pattern[start_index:end_index]
                    pattern_distance = compute_pattern_distance(generated_playlist, history_pattern, spotify)
            except SpotifyException:
                spotify = change_credentials()
            except Exception as e:
                print(e)
                print(f"Couldn't compute Pattern Distance for playlist {playlist_data}:  its length ({len(generated_playlist)}) differs from the length ({len(history_pattern)}) of the corresponding history pattern\n")
                break
            if pattern_distance:
                print(f"Result #{i}:\nListening history: {playlist_data[0]}\nDay: {playlist_data[1]}\nHour: {playlist_data[2]}\nMethod: {playlist_data[3]}\nPD: {pattern_distance}\n")
                i += 1
                with open("data/results.bin", "ab") as file:
                        pickle.dump({playlist_data: (pattern_distance, len(generated_playlist))}, file)
                break


    print("The new generated playlists have been uploaded on 'data/results.bin'")

def generate_spreadsheet(results):
    data = []
    methods = ["our_method", "rec-1", "rec-2", "hyb-1"]
    for key, value in results.items():
        LH_filename, day, hour, method = key
        if value and LH_filename != "normal_mode":
            all_playlists = True
            for m in methods:
                if not results.get((LH_filename, day, hour, m), None):
                    all_playlists = False
            if all_playlists:
                data.append({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': value[1], 'Pattern_Distance': value[0]})
    
    if data:
        df = pd.DataFrame(data)
        df.to_excel("graphs/playlists_results.xlsx", index=False)
        print("Spreadsheet generated: playlist_results.xlsx")

        variability_rankings = df.groupby('LH_filename')['Pattern_Distance'].quantile(0.75) - df.groupby('LH_filename')['Pattern_Distance'].quantile(0.25)
        variability_rankings = variability_rankings.sort_values(ascending=False)
        print("Variability Rankings (Descending):")
        print(variability_rankings)

        # Create a graph for each LH_filename
        for lh_filename in df['LH_filename'].unique():
            plt.figure(figsize=(10, 6))
            lh_data = df[df['LH_filename'] == lh_filename]
            grouped_df = lh_data.groupby('Method')['Pattern_Distance'].mean()

            # Create bar plot
            grouped_df.plot(kind='bar', color=['blue', 'orange', 'green', 'red'])
            plt.title(f'Media di Pattern Distance per LH_filename: {lh_filename}')
            plt.xlabel('Method')
            plt.ylabel('Media di Pattern Distance')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Save graph as PNG
            plt.savefig(f'graphs/average_pattern_distances/{lh_filename}.png')

        print("Graphs generated for each LH_filename.")



def generate_boxplot(results):
    data = []
    methods = ["our_method", "rec-1", "rec-2", "hyb-1"]
    for key, value in results.items():
        LH_filename, day, hour, method = key
        if value and LH_filename != "normal_mode":
            all_playlists = True
            for m in methods:
                if not results.get((LH_filename, day, hour, m), None):
                    all_playlists = False
            if all_playlists:
                data.append({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': value[1], 'Pattern_Distance': value[0]})
    
    if data:
        df = pd.DataFrame(data)
        df.to_excel("graphs/playlists_results.xlsx", index=False)
        print("Spreadsheet generated: playlist_results.xlsx")

        variability_rankings = df.groupby('LH_filename')['Pattern_Distance'].quantile(0.75) - df.groupby('LH_filename')['Pattern_Distance'].quantile(0.25)
        variability_rankings = variability_rankings.sort_values(ascending=False)
        print("Variability Rankings (Descending):")
        print(variability_rankings)

        # Create boxplot for each LH_filename
        for lh_filename in df['LH_filename'].unique():
            plt.figure(figsize=(12, 8))
            lh_data = df[df['LH_filename'] == lh_filename]
            sns.boxplot(x='Method', y='Pattern_Distance', data=lh_data, palette='Set3')
            plt.title(f'Boxplot della Pattern Distance Media per LH_filename: {lh_filename}')
            plt.xlabel('Method')
            plt.ylabel('Media della Pattern Distance')
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Save boxplot as PNG
            plt.savefig(f'graphs/boxplots/boxplot_{lh_filename}.png')

        print("Boxplots generated for each LH_filename.")




def generate_single_listening_history_graphs(results):
    data = []
    methods = ["our_method", "rec-1", "rec-2", "hyb-1"]
    for key, value in results.items():
        LH_filename, day, hour, method = key
        if value:
            all_playlists = True
            for m in methods:
                if not results.get((LH_filename, day, hour, m), None):
                    all_playlists = False
            if all_playlists:
                data.append({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': value[1], 'Pattern_Distance': value[0]})
    
    if data:
        df = pd.DataFrame(data)
        df.to_excel("graphs/playlists_results.xlsx", index=False)
        print("Spreadsheet generated: playlist_results.xlsx")

        # Create single listening history graphs
        for lh_filename in df['LH_filename'].unique():
            plt.figure(figsize=(10, 6))
            lh_data = df[df['LH_filename'] == lh_filename]
            for method in methods:
                method_data = lh_data[lh_data['Method'] == method]
                hourly_average = method_data.groupby('Hour')['Pattern_Distance'].mean()
                plt.plot(hourly_average.index, hourly_average.values, label=method, marker='o', linestyle='-')

            plt.title(f'Pattern Distance Media per LH_filename: {lh_filename}')
            plt.xlabel('Ora')
            plt.ylabel('Pattern Distance Media')
            plt.xticks(range(24))
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            # Save graph as PNG
            plt.savefig(f'graphs/single_listening_history_graphs/{lh_filename}.png')

        print("Single listening history graphs generated.")


def main():
    playlists = retrieve_playlists()
    if playlists:
        compute_playlist_pattern_distances(playlists)
    else:
        print("No new generated playlists found")

    results = retrieve_results()
    generate_spreadsheet(results)
if __name__ == "__main__":
    main()