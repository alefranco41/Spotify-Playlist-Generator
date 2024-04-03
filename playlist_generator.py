import step1
import step2
import other_methods
import listening_history_manager
import evaluation
import sys
import signal
import inspect

def handler(signal_received, frame):
    # Ottieni l'elenco dei frame nello stack
    stack = inspect.stack()

    print(stack)
    

    

def main():
    signal.signal(signal.SIGINT, handler)
    listening_history_file_data = []
    listening_history_file = input(step1.input_message)
    if listening_history_file:
        listening_history_file_data = step1.csv_to_dict(listening_history_file)
    
    if listening_history_file_data:
        prefix_name = step1.compute_prefix_name(listening_history_file)
    else:
        prefix_name = "normal_mode"
        print("Since a valid listening history file was not provided,\nthe software will try to generate a playlist by using the last 50 songs played through the Spotify API")

    #listening history processing
    periods = step1.compute_periods(listening_history_file_data, prefix_name)
    listening_history = step1.compute_listening_history(periods, prefix_name)
    listening_habits = step1.compute_listening_habits(periods)
    current_hour_listening_habits = {period:listening_habits.get(period, None) for period in [listening_history_manager.current_hour]}
    current_hour_listening_history = {hour:songs for hour, songs in listening_history.items() if hour == listening_history_manager.current_hour}
    
    if not current_hour_listening_habits:
        print(f"No listening habits detected for hour {listening_history_manager.current_hour}")
        sys.exit()
        
    if not current_hour_listening_history:
        print(f"No listening history detected for hour {listening_history_manager.current_hour}")
        sys.exit()
    
    most_similar_song_sets = step2.retrieve_most_similar_song_set(prefix_name, listening_history_manager.current_hour)

    if most_similar_song_sets:
        ans = input(f"A file containing the most similar song set for hour {listening_history_manager.current_hour} has been found, would you like to skip to step 2? (y/n): ")
        if ans != 'y':
            most_similar_song_sets = None
    
    #step 1
    if not most_similar_song_sets:        
        clusterings = step1.compute_clusterings(current_hour_listening_history)
        clustering_song_sets = step1.generate_clustering_song_sets(clusterings)
        most_similar_song_sets = step1.compute_most_similar_song_sets(clustering_song_sets, periods, current_hour_listening_habits)
        step1.upload_most_similar_song_sets(most_similar_song_sets, prefix_name)

    #step 2
    timestamp_key = step2.get_timestamp_key(periods)
    history_patterns = step2.compute_best_history_patterns(periods, listening_history_manager.current_day, timestamp_key, prefix_name)
    optimal_solutions_indexes = step2.compute_optimal_solution_indexes(history_patterns, most_similar_song_sets)
    our_method_playlists = step2.retrieve_optimal_solution_songs(optimal_solutions_indexes, most_similar_song_sets)
    our_method_playlists = step2.create_playlists_dict(our_method_playlists, listening_history_manager.current_day, history_patterns, prefix_name)
    
    #experimental phase
    playlists_rec_1 = other_methods.get_rec_1_recommendations(current_hour_listening_history,prefix_name, listening_history_manager.current_day)
    playlists_rec_2 = other_methods.get_rec_2_recommendations(current_hour_listening_history,prefix_name, listening_history_manager.current_day)
    playlists_hyb_1, best_history_patterns = other_methods.get_hyb_1_recommendations(current_hour_listening_history, periods,prefix_name, listening_history_manager.current_day)
    other_methods_playlists = other_methods.create_playlists_dict(playlists_rec_1, playlists_rec_2, playlists_hyb_1, best_history_patterns, prefix_name)
    all_playlists = {**our_method_playlists, **other_methods_playlists}
    #step2.create_playlists(all_playlists)
    evaluation.compute_playlist_pattern_distances(all_playlists)
    results = evaluation.retrieve_results()
    evaluation.generate_spreadsheet(results)

        
if __name__ == "__main__":
    main()