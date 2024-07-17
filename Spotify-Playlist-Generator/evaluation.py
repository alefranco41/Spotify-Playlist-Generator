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


def compute_all_data():
    all_patterns = []
    for listening_history_file in os.listdir(directory_name):
        listening_history_file_path = os.path.join(directory_name, listening_history_file)
        listening_history_file_data = csv_to_dict(listening_history_file_path)
        prefix_name = compute_prefix_name(listening_history_file)
        
        if listening_history_file_data:
            periods = compute_periods(listening_history_file_data, prefix_name)
            listening_history = compute_listening_history(periods, prefix_name)
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
from collections import OrderedDict

def compute_listening_history_data():
    average_pattern_lengths = {}
    data = []
    columns = ['File di cronologia', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica', 'Totale']

    prefix_name_ordered = [f"LH{i}" for i in range(1,27)]
    for prefix_name in prefix_name_ordered:
        for file_path in os.listdir("data"):
            current_prefix_name = file_path.split('_')[0]
            if current_prefix_name != prefix_name or current_prefix_name in ['LH25', 'LH26']:
                continue

            file_path = os.path.join("data", file_path)
            if file_path.endswith("listening_history.bin"):
                with open(file_path, "rb") as file:
                    listening_history = pickle.load(file)

                total_songs = 0
                songs_periods = {}
                days = set()
                daily_songs = {'Monday':0,'Tuesday':0,'Wednesday':0,'Thursday':0,'Friday':0,'Saturday':0,'Sunday':0,}
                for (day,hour), songs in listening_history.items():
                    days.add(day)                
                    daily_songs[day] += len(songs)
                    total_songs += len(songs)
                    songs_periods[(day,hour)] = len(songs)
                

            
                
                print(prefix_name, daily_songs, sum(daily_songs.values()))

                total_songs = sum(daily_songs.values())
                row = [prefix_name] + [daily_songs[day] for day in daily_songs] + [total_songs]
                data.append(row)

                incidence = {}
                for (current_day,hour), total in songs_periods.items():
                    incidence[(current_day,hour)] = round((100 * total / sum([len(songs) for (day,hour), songs in listening_history.items() if day == current_day])),2)

                # Creare un dizionario di default per contenere tutte le ore del giorno con incidenza 0
                full_day_incidence = {hour: 0 for hour in range(24)}

                for current_day in days:
                    """plt.figure(figsize=(15, 6))
                    plt.xticks(range(24))"""

                    # Aggiorna il dizionario full_day_incidence con i valori effettivi di incidenza
                    for hour in range(24):
                        if (current_day, hour) in incidence:
                            full_day_incidence[hour] = incidence[(current_day, hour)]

                    """x = list(full_day_incidence.keys())
                    y = list(full_day_incidence.values())

                    plt.bar(x, y)
                    plt.title(f"{prefix_name}'s {current_day} song incidence by Hour (Total Songs: {sum([len(songs) for (day,hour), songs in listening_history.items() if day == current_day])})")

                    plt.xlabel("Period")
                    plt.ylabel("Incidence (%)")

                    plt.savefig(f"graphs/daily_song_incidences/{current_day}/{prefix_name}_incidence_{current_day}.png")"""
                
                periods = compute_periods([], prefix_name)
                listening_history_patterns = compute_listening_history_patterns(periods, "endTime")
                
                for current_day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                    current_day_patterns = [(pattern, hour) for hour, daily_patterns in listening_history_patterns.items() for day, patterns in daily_patterns.items() for pattern in patterns if day == current_day]
                    longest_pattern_length = {}

                    for current_hour in range(24):
                        current_day_hour_patterns = [len(pattern) for pattern, hour in current_day_patterns if hour == current_hour]
                        if current_day_hour_patterns:
                            longest_pattern_length[current_hour] = max(current_day_hour_patterns)
                        else:
                            longest_pattern_length[current_hour] = 0

                    # Creazione di una lista di lunghezza fissa per le ore da 0 a 23
                    x = list(range(24))
                    # Popolazione della lista y con i valori medi delle lunghezze dei pattern
                    y = [longest_pattern_length.get(hour, 0) for hour in range(24)]

                    plt.figure(figsize=(15, 6))
                    plt.xticks(range(24))
                    plt.bar(x, y)
                    plt.title(f"{prefix_name}'s {current_day} longest pattern lengths by Hour")
                    plt.xlabel("Period")
                    plt.ylabel("Length")
                    plt.savefig(f"graphs/daily_longest_patterns/{current_day}/{prefix_name}_longest_patterns_{current_day}.png")
                    plt.clf()  # Pulizia del grafico corrente per la prossima iterazione

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
                
        df = pd.DataFrame(data, columns=columns)
        df.to_excel("listening_history_summary.xlsx", index=False)

            # Plotting data
            #plot_data("Longest Pattern Length by Hour", longest_pattern_hour, xlabel="Hour", ylabel="Length", name=f"graphs/longest_patterns/longest_pattern{prefix_name}.png", y_limit=125)
            #plot_data("Average Pattern Length by Hour", average_pattern_length_hour, xlabel="Hour", ylabel="Average Length", name=f"graphs/average_pattern_lengths/average_pattern_lengths_{prefix_name}.png")
    #sorted_data = dict(sorted(average_pattern_lengths.items(), key=lambda x: int(x[0][2:])))
    #print(sorted_data)
    #plot_data("Average Pattern Lengths", sorted_data, xlabel="Listening History", ylabel="Average pattern length", name=f"graphs/average_pattern_lengths.png")"""

def retrieve_playlists(file=None):
    playlists = {}
    if not file:
        file = "data/playlists.bin"
    try:
        with open(file, "rb") as file:
            try:
                while True:
                    playlists.update(pickle.load(file))
            except (EOFError):
                pass
    except FileNotFoundError:
        pass

    return playlists



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
    if os.path.exists("data/results_1_month.bin"):
        with open("data/results_1_month.bin", "rb") as file:
            try:
                while True:
                    result = pickle.load(file)
                    results.update(result)
            except EOFError:
                pass
    return results

def retrieve_results2():
    results = {}
    filenames = [("results_1_month.bin",1),("results_3_months.bin",3),("results_6_months.bin",6),("results_1_year.bin",12)]
    for filename, n in filenames:
        with open(os.path.join('data', filename), "rb") as file:
            try:
                while True:
                    result = pickle.load(file)
                    new_result = {}
                    for key in result.keys():
                        new_result[(key[0], key[1], key[2], key[3], n)] = result[key]
                    
                    results.update(new_result)
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


def compute_segment_distance(playlist_features, pattern_features):
    sum = 0
    for i in range(len(generated_playlist_features)):
        generated_playlist_features = [feature for feature in playlist_features[i].values() if not isinstance(feature, str)]
        history_pattern_features = [feature for feature in pattern_features[i].values() if not isinstance(feature, str)]
        sum += euclidean(generated_playlist_features, history_pattern_features)
    return sum
    
def compute_pattern_distance(generated_playlist, history_pattern, spotify):
    generated_playlist_features = get_features(generated_playlist, spotify)
    history_pattern_features = get_features(history_pattern, spotify)
    vertex_distance = compute_vertex_distance(generated_playlist_features, history_pattern_features)
    segment_distance = compute_segment_distance(generated_playlist_features, history_pattern_features)
    return vertex_distance + segment_distance


def compute_playlist_pattern_distances(playlists):
    #existing_results = retrieve_results()

    print("Results for the generated playlists:\n")
    #i = len(existing_results) + 1  # Start counting from the next index


    spotify = change_credentials()

    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        #if playlist_data in existing_results:
            #continue  # Skip if already computed

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
                print(f"Result :\nListening history: {playlist_data[0]}\nDay: {playlist_data[1]}\nHour: {playlist_data[2]}\nMethod: {playlist_data[3]}\nPD: {pattern_distance}\n")
                #i += 1
                with open("data/results_1_month.bin", "ab") as file:
                        pickle.dump({playlist_data: (pattern_distance, len(generated_playlist))}, file)
                break


def compute_playlist_pattern_distances(playlists):
    spotify = change_credentials()
    results = {}
    for playlist_data, (generated_playlist, history_pattern) in playlists.items():
        while True:
            pattern_distance = None
            try:
                if len(generated_playlist) == len(history_pattern):
                    pattern_distance = compute_pattern_distance(generated_playlist, history_pattern, spotify)
            except SpotifyException:
                spotify = change_credentials()
            except Exception as e:
                break
            if pattern_distance:
                playlist_features = get_features(generated_playlist, spotify)
                pattern_features = get_features(history_pattern, spotify)
                vertex_distance = compute_vertex_distance(playlist_features, pattern_features)
                segment_distance = compute_segment_distance(playlist_features, pattern_features)
                pattern_distance = vertex_distance + segment_distance
                results[playlist_data] = pattern_distance
    return results


def generate_spreadsheet(results):
    data = []
    for key, value in results.items():
        LH_filename, day, hour, method = key
        if value and LH_filename != "normal_mode":
            data.append({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': int(value[1]), 'Pattern_Distance': value[0]})
            if LH_filename == "LH1":
                print({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': value[1], 'Pattern_Distance': value[0]})
    
    df = pd.DataFrame(data)
    #df.to_excel("graphs/playlists_results.xlsx", index=False)


    # Raggruppa per lunghezza della playlist e metodo e calcola la media delle distanze dei pattern
    grouped_df = df.groupby(['Playlist_Length', 'Method'])['Pattern_Distance'].mean().unstack()

    # Calcola la differenza tra le medie di our_method e hyb-1 per ogni lunghezza della playlist
    difference = grouped_df['our_method'] - grouped_df['hyb-1']

    # Trova il valore di Playlist_Length che ha prodotto la massima differenza
    max_difference_value = difference.idxmax()
    max_difference = difference.max()

    print(f"The maximum difference in pattern distance occurs at Playlist_Length={max_difference_value} with a difference of {max_difference}")


    plt.figure(figsize=(10, 6))
    for method in ['our_method', 'hyb-1']:
        method_data = df[df['Method'] == method]
        grouped_df = method_data.groupby('Playlist_Length')['Pattern_Distance'].mean()
        plt.plot(grouped_df.index, grouped_df.values, label=method, marker='o', linestyle='-')

    plt.title(f"Average Pattern Distances by Playlist Length")
    plt.xlabel('Playlist Length')
    plt.ylabel('Average Pattern Distance')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.legend()
    plt.savefig(f'graphs/hyb-1_our-method_average_PD_by_playlist_length_1_month.png')

    if data:
        df = pd.DataFrame(data)
        generate_daily_average_pattern_distance_graphs(df)
        df.to_excel("graphs/playlists_results_1_month.xlsx", index=False)
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
            plt.title(f"{lh_filename}s average Pattern Distances")
            plt.xlabel('Method')
            plt.ylabel('Average Pattern Distance')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Save graph as PNG
            plt.savefig(f'graphs/average_pattern_distances/{lh_filename}_1_month.png')

        print("Graphs generated for each LH_filename.")

def generate_daily_average_pattern_distance_graphs(results):
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for lh_filename in results['LH_filename'].unique():
        for day in days_of_week:
            plt.figure(figsize=(10, 6))
            lh_data_day = results[(results['LH_filename'] == lh_filename) & (results['Day'] == day)]
            if not lh_data_day.empty:
                grouped_df = lh_data_day.groupby(['Day', 'Method'])['Pattern_Distance'].mean().unstack()
                
                # Create bar plot
                grouped_df.plot(kind='bar', color=['blue', 'orange', 'green', 'red'])
                plt.title(f"{day}'s average Pattern Distances for {lh_filename}")
                plt.xlabel('Method')
                plt.ylabel('Average Pattern Distance')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                
                # Save graph as PNG
                plt.savefig(f'graphs/daily_average_pattern_distances/{day}/daily_average_pattern_distances_{day}_{lh_filename}_1_month.png')
                plt.close()



def generate_boxplot(results):
    data = []
    for key, value in results.items():
        LH_filename, day, hour, method = key
        if value and LH_filename != "normal_mode":
            data.append({'LH_filename': LH_filename, 'Day': day, 'Hour': hour, 'Method': method, 'Playlist_Length': value[1], 'Pattern_Distance': value[0]})
    
    if data:
        df = pd.DataFrame(data)
        generate_daily_boxplot(df)
        df.to_excel("graphs/playlists_results_1_month.xlsx", index=False)
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
            plt.title(f"{lh_filename}'s average Pattern Distance boxplot")
            plt.xlabel('Method')
            plt.ylabel('Average Pattern Distance')
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Save boxplot as PNG
            plt.savefig(f'graphs/average_pattern_distances_boxplots/average_pattern_distances_boxplot_{lh_filename}_1_month.png')

        print("Boxplots generated for each LH_filename.")


def generate_daily_boxplot(results):
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for day in days_of_week:
        for lh_filename in results['LH_filename'].unique():
            plt.figure(figsize=(12, 8))
            lh_data_day = results[(results['LH_filename'] == lh_filename) & (results['Day'] == day)]
            if not lh_data_day.empty:
                sns.boxplot(x='Method', y='Pattern_Distance', data=lh_data_day, palette='Set3')
                plt.title(f"{lh_filename}'s {day} Average Pattern Distance boxplot")
                plt.xlabel('Method')
                plt.ylabel('Average Pattern Distance')
                plt.xticks(rotation=45)
                plt.tight_layout()

                # Save boxplot as PNG
                plt.savefig(f'graphs/daily_average_pattern_distances_boxplots/{day}/boxplot_{day}_{lh_filename}_1_month.png')
                plt.close()


from scipy.stats import ttest_ind_from_stats
import numpy as np

def calculate_stats(results):
    # Organizza i dati in un DataFrame
    data = []
    for (LH_filename, day, hour, method, time_interval), value in results.items():
        data.append({
            'LH_filename': LH_filename,
            'Day': day,
            'Hour': hour,
            'Method': method,
            'Time_Interval': time_interval,
            'Pattern_Distance': value[0]
        })

    df = pd.DataFrame(data)

    # Calcola la media e la varianza per ogni (LH_filename, method, time_interval)
    stats = df.groupby(['LH_filename', 'Method', 'Time_Interval'])['Pattern_Distance'].agg(['mean', 'var']).reset_index()
    
    # Visualizzazione dei dati con box plot per ciascun LH_filename
    lh_filenames = df['LH_filename'].unique()
    for lh_filename in lh_filenames:
        plt.figure(figsize=(12, 8))
        sns.boxplot(x='Time_Interval', y='Pattern_Distance', hue='Method', data=df[df['LH_filename'] == lh_filename])
        plt.title(f'Distribuzione delle Distanze dei Pattern per Metodo e Intervallo di Tempo ({lh_filename})')
        plt.savefig(f"distribuzione_{lh_filename}.png")
        plt.close()

    # Perform the t-test for the 3-month interval
    lh_filenames = df['LH_filename'].unique()
    results = {}

    for lh_filename in lh_filenames:
        mean_our_method = stats[(stats['LH_filename'] == lh_filename) & 
                                (stats['Method'] == 'our_method') & 
                                (stats['Time_Interval'] == 3)]['mean'].values[0]
        var_our_method = stats[(stats['LH_filename'] == lh_filename) & 
                               (stats['Method'] == 'our_method') & 
                               (stats['Time_Interval'] == 3)]['var'].values[0]
        n_our_method = len(df[(df['LH_filename'] == lh_filename) & 
                              (df['Method'] == 'our_method') & 
                              (df['Time_Interval'] == 3)])

        mean_hyb1 = stats[(stats['LH_filename'] == lh_filename) & 
                          (stats['Method'] == 'hyb-1') & 
                          (stats['Time_Interval'] == 3)]['mean'].values[0]
        var_hyb1 = stats[(stats['LH_filename'] == lh_filename) & 
                         (stats['Method'] == 'hyb-1') & 
                         (stats['Time_Interval'] == 3)]['var'].values[0]
        n_hyb1 = len(df[(df['LH_filename'] == lh_filename) & 
                        (df['Method'] == 'hyb-1') & 
                        (df['Time_Interval'] == 3)])

        # Perform t-test
        t_stat, p_value = ttest_ind_from_stats(mean1=mean_our_method, std1=np.sqrt(var_our_method), nobs1=n_our_method,
                                               mean2=mean_hyb1, std2=np.sqrt(var_hyb1), nobs2=n_hyb1)
        
        results[lh_filename] = (t_stat, p_value)

    return stats, results


def generate_single_listening_history_graphs(results):
    data = []
    methods = ["our_method", "hyb-1"]
    time_intervals = [1, 3, 6, 12]
    
    filtered_results = {}

    for key, value in results.items():
        if isinstance(key[2], tuple):
            new_key = (key[0], key[1], key[2][1], key[3], key[4])
        else:
            new_key = key

        filtered_results[new_key] = value

    for key, value in filtered_results.items():
        LH_filename, day, hour, method, time_interval = key
        
        if value:
            data.append({
                'LH_filename': LH_filename, 
                'Day': day, 
                'Hour': hour, 
                'Method': method, 
                'Time_Interval': time_interval, 
                'Playlist_Length': value[1], 
                'Pattern_Distance': value[0]
            })

    if data:
        df = pd.DataFrame(data)
        df.to_excel("graphs/playlists_results_time_intervals.xlsx", index=False)
        print("Spreadsheet generated: playlists_results_time_intervals.xlsx")

        # Create single listening history graphs
        for lh_filename in df['LH_filename'].unique():
            plt.figure(figsize=(10, 6))
            lh_data = df[df['LH_filename'] == lh_filename]
            for time_interval in time_intervals:
                for method in methods:
                    interval_method_data = lh_data[(lh_data['Method'] == method) & (lh_data['Time_Interval'] == time_interval)]
                    hourly_average = interval_method_data.groupby('Hour')['Pattern_Distance'].mean()
                    label = f"{time_interval} mesi - {method}"
                    plt.plot(hourly_average.index, hourly_average.values, label=label, marker='o', linestyle='-')

            plt.title(f"{lh_filename}'s Average Pattern Distance Line Chart")
            plt.xlabel('Hour')
            plt.ylabel('Average Pattern Distance')
            plt.xticks(range(24))
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            # Save graph as PNG
            plt.savefig(f'{lh_filename}_time_intervals.png')
            plt.close()

        print("Single listening history graphs generated.")

def generate_daily_average_pattern_distance_line_charts(results):
    i = 0
    methods = ["our_method", "hyb-1"]
    for day in results['Day'].unique():
        plt.figure(figsize=(10, 6))  # Sposta la creazione della figura all'esterno del ciclo
        day_data = results[results['Day'] == day]
        for lh_filename in day_data['LH_filename'].unique():
            lh_data = day_data[day_data['LH_filename'] == lh_filename]
            for method in methods:
                method_data = lh_data[lh_data['Method'] == method]
                daily_average = method_data.groupby('Hour')['Pattern_Distance'].mean()
                daily_average.index = daily_average.index.get_level_values('Hour')
                plt.plot(daily_average.index, daily_average.values, label=method, marker='o', linestyle='-')

            plt.title(f"{lh_filename}'s {day} Average Pattern Distance line chart")
            plt.xlabel('Hour')
            plt.ylabel('Average Pattern Distance')
            plt.xticks(range(24))
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            # Save graph as PNG
            plt.savefig(f'graphs/daily_average_pattern_distances_line_charts/{day}/daily_average_pattern_distances_line_charts_{day}_{lh_filename}_1_month.png')
            plt.close()
            i+=1
            print(i)

    print("Daily average pattern distance line charts generated.")




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







def sasso():
    data_global = []
    #data_specific = []

    prefix_name_ordered = [f"LH{i}" for i in range(1, 27)]
    
    # Fogli di calcolo globali
    for prefix_name in prefix_name_ordered:
        periods = compute_periods([], prefix_name)
        listening_history_patterns = compute_listening_history_patterns(periods, "endTime")

        max_lengths_per_day = {}
        for current_day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            current_day_patterns = [(pattern, hour) for hour, daily_patterns in listening_history_patterns.items() for day, patterns in daily_patterns.items() if day == current_day for pattern in patterns]
            max_length_per_hour = {hour: 0 for hour in range(24)}  # Initialize with 0 for each hour
            for pattern, hour in current_day_patterns:
                max_length_per_hour[hour] = max(max_length_per_hour[hour], len(pattern))
            
            max_lengths_per_day[current_day] = (max_length_per_hour.values())

        #total_max_length = sum(max_lengths_per_day.values())
        data_global.append([prefix_name, *max_lengths_per_day.values()])

    """# Fogli di calcolo specifici
    for prefix_name in prefix_name_ordered:
        periods = compute_periods([], prefix_name)
        listening_history_patterns = compute_listening_history_patterns(periods, "endTime")

        max_lengths_per_hour = {hour: 0 for hour in range(24)}
        for current_hour in range(24):
            current_hour_patterns = [(pattern, hour) for hour, daily_patterns in listening_history_patterns.items() for day, patterns in daily_patterns.items() for pattern in patterns if hour == current_hour]
            if current_hour_patterns:
                max_lengths_per_hour[current_hour] = max(len(pattern) for pattern, hour in current_hour_patterns)
            else:
                max_lengths_per_hour[current_hour] = 0

        data_specific.append([[hour, *max_lengths_per_hour.values(), sum(max_lengths_per_hour.values())] for hour in range(24)])"""

    return data_global#, data_specific

from openpyxl import Workbook
import numpy as np

def sasso():
    data_global = []

    prefix_name_ordered = [f"LH{i}" for i in range(1, 27)]
    
    # Fogli di calcolo globali
    for prefix_name in prefix_name_ordered:
        periods = compute_periods([], prefix_name)
        listening_history_patterns = compute_listening_history_patterns(periods, "endTime")

        avg_lengths_per_hour = {hour: [] for hour in range(24)}
        for hour, daily_patterns in listening_history_patterns.items():
            for day, patterns in daily_patterns.items():
                for pattern in patterns:
                    avg_lengths_per_hour[hour].append(len(pattern))
        
        avg_lengths_per_hour = {hour: round(np.mean(lengths), 1) if lengths else 0 for hour, lengths in avg_lengths_per_hour.items()}
        
        data_global.append([prefix_name, *avg_lengths_per_hour.values()])

    return data_global

def generate_workbook(data_global):
    # Foglio di calcolo globale
    wb_global = Workbook()
    ws_global = wb_global.active
    ws_global.title = "Global"

    # Inserimento dati nel foglio di calcolo globale
    ws_global.append(['Prefix Name', *range(24)])
    for row in data_global:
        ws_global.append(row)

    return wb_global

