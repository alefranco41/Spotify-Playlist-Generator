import step1
import step2
import other_methods
import listening_history_manager
import evaluation
import sys
from datetime import datetime

def parse_arguments():
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    valid_hours = [i for i in range(0, 24)]
    args = sys.argv[1:]

    current_day = None
    current_hour = None
    listening_history_file = None
    step2 = False
    skip_existing_playlists = False

    for i in range(len(args)-1):
        if args[i] == "-d" and args[i+1] in valid_days:
            current_day = args[i+1]
        if args[i] == "-h" and int(args[i+1]) in valid_hours:
            current_hour = int(args[i+1])
        if args[i] == "-f":
            listening_history_file = args[i+1]
        if args[i] == "--force-step-2" or (i == len(args)-2 and args[i+1] == "--force-step-2"):
            step2 = True
        if args[i] == "--skip-existing-playlists" or (i == len(args)-2 and args[i+1] == "--skip-existing-playlists"):
            skip_existing_playlists = True

    if not current_day:
        current_day =  datetime.now().strftime("%A")
    if current_hour is None:
        current_hour = int(datetime.now().hour)
        
    if skip_existing_playlists and listening_history_file:
        prefix_name = step1.compute_prefix_name(listening_history_file)
        playlists = evaluation.retrieve_playlists()
        if playlists and playlists.get((prefix_name,current_day,current_hour,"our_method"), None):
            playlist_rec_1 = playlists.get((prefix_name,current_day,current_hour,"rec-1"), None)
            playlist_rec_2 = playlists.get((prefix_name,current_day,current_hour,"rec-2"), None)
            playlist_hyb_1 = playlists.get((prefix_name,current_day,current_hour,"hyb-1"), None)
            if playlist_rec_1 is not None or playlist_rec_2 is not None or playlist_hyb_1 is not None:
                print(f"Playlists already found for day: {current_day}, hour: {current_hour}, listening history: {listening_history_file}")
                sys.exit()
    return current_day, current_hour, listening_history_file, step2

def experimental_phase(prefix_name, current_hour_listening_history, periods, our_method_playlists, current_day):
    playlists_rec_1 = other_methods.get_rec_1_recommendations(current_hour_listening_history,prefix_name, current_day)
    playlists_rec_2 = other_methods.get_rec_2_recommendations(current_hour_listening_history,prefix_name, current_day)
    playlists_hyb_1, best_history_patterns = other_methods.get_hyb_1_recommendations(current_hour_listening_history, periods,prefix_name, current_day)
    other_methods_playlists = other_methods.create_playlists_dict(playlists_rec_1, playlists_rec_2, playlists_hyb_1, best_history_patterns, prefix_name, current_day)
    #step2.create_playlists(other_methods_playlists)
    
    #experimental phase
    all_playlists = {**our_method_playlists, **other_methods_playlists}
    evaluation.compute_playlist_pattern_distances(all_playlists)
    results = evaluation.retrieve_results()
    evaluation.generate_spreadsheet(results)

def main():
    current_day, current_hour, listening_history_file, force_step2 = parse_arguments()
    listening_history_file_data = []
    
    if not listening_history_file:
        listening_history_file = input(step1.input_message)

    if listening_history_file:
        listening_history_file_data = listening_history_manager.csv_to_dict(listening_history_file)
    
    if listening_history_file_data:
        prefix_name = step1.compute_prefix_name(listening_history_file)
    else:
        prefix_name = "normal_mode"
        print("Since a valid listening history file was not provided,\nthe software will try to generate a playlist by using the last 50 songs played through the Spotify API")

    #listening history processing
    periods = step1.compute_periods(listening_history_file_data, prefix_name)
    listening_history = step1.compute_listening_history(periods, prefix_name)
    listening_habits = step1.compute_listening_habits(periods, prefix_name)
    current_hour_listening_habits = {period:listening_habits.get(period, None) for period in [current_hour]}
    current_hour_listening_history = {hour:songs for hour, songs in listening_history.items() if hour == current_hour}
    if not current_hour_listening_habits:
        print(f"No listening habits detected for hour {current_hour}")
        sys.exit(2)
        
    if not current_hour_listening_history:
        print(f"No listening history detected for hour {current_hour}")
        sys.exit(2)
    
    most_similar_song_sets = step2.retrieve_most_similar_song_set(prefix_name, current_hour)
    ans = None
    if most_similar_song_sets and not force_step2:
        ans = input(f"A file containing the most similar song set for hour {current_hour} has been found, would you like to skip to step 2? (y/n): ")
        if ans != 'y':
            most_similar_song_sets = None
    elif most_similar_song_sets and force_step2:
        ans = 'y'
    
    
    #step 1
    if not most_similar_song_sets or ans != 'y':
        clusterings = step1.compute_clusterings(current_hour_listening_history)
        clustering_song_sets = step1.generate_clustering_song_sets(clusterings)
        most_similar_song_sets = step1.compute_most_similar_song_sets(clustering_song_sets, periods, current_hour_listening_habits)
        step1.upload_most_similar_song_sets(most_similar_song_sets, prefix_name)

    #step 2
    timestamp_key = step2.get_timestamp_key(periods)
    history_patterns = step2.compute_best_history_patterns(periods, current_day, timestamp_key, prefix_name)
    optimal_solutions_indexes = step2.compute_optimal_solution_indexes(history_patterns, most_similar_song_sets)
    our_method_playlists = step2.retrieve_optimal_solution_songs(optimal_solutions_indexes, most_similar_song_sets)
    our_method_playlists = step2.create_playlists_dict(our_method_playlists, current_day, history_patterns, prefix_name)
    #step2.create_playlists(our_method_playlists)

    #other methods
    experimental_phase(prefix_name, current_hour_listening_history, periods, our_method_playlists, current_day)

        
if __name__ == "__main__":
    main()