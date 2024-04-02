import step1
import step2
import other_methods
import listening_history_manager
import evaluation

def main():
    listening_history_file_data = []
    listening_history_file = input(step1.input_message)
    if listening_history_file:
        listening_history_file_data = step1.csv_to_dict(listening_history_file)
    
    if listening_history_file_data:
        prefix_name = step1.compute_prefix_name(listening_history_file)
    else:
        prefix_name = "normal_mode"
        print("Since a valid listening history file was not provided,\nthe software will try to generate a playlist by using the last 50 songs played through the Spotify API")

    periods = step1.compute_periods(listening_history_file_data, prefix_name)
    listening_history = step1.compute_listening_history(periods, prefix_name)
    listening_habits = step1.compute_listening_habits(periods)
    print("Computed listening habits ")
    listening_habits_periods = {period:listening_habits.get(period, None) for period in [listening_history_manager.current_hour]}

    if listening_habits_periods and any(value is not None for value in listening_habits_periods.values()): 
        listening_history_filtered = {hour:songs for hour, songs in listening_history.items() if hour == listening_history_manager.current_hour}
        if listening_history_filtered and any(len(value) != 0 for value in listening_history_filtered.values()):
            clusterings = step1.compute_clusterings(listening_history_filtered)
            if clusterings:
                clustering_song_sets = step1.generate_clustering_song_sets(clusterings)
                most_similar_song_sets = step1.compute_most_similar_song_sets(clustering_song_sets, periods, listening_habits_periods)

                if most_similar_song_sets:
                    step1.upload_most_similar_song_sets(most_similar_song_sets, prefix_name)
                    timestamp_key = step2.get_timestamp_key(periods)
                    history_patterns = step2.compute_best_history_patterns(periods, listening_history_manager.current_day, timestamp_key, prefix_name)
                    if history_patterns:
                        optimal_solutions_indexes = step2.compute_optimal_solution_indexes(history_patterns, most_similar_song_sets)
                        our_method_playlists = step2.retrieve_optimal_solution_songs(optimal_solutions_indexes, most_similar_song_sets)
                        our_method_playlists = step2.create_playlists_dict(our_method_playlists, listening_history_manager.current_day, history_patterns, prefix_name)
                        playlists_rec_1 = other_methods.get_rec_1_recommendations(listening_history_filtered,prefix_name, listening_history_manager.current_day)
                        playlists_rec_2 = other_methods.get_rec_2_recommendations(listening_history_filtered,prefix_name, listening_history_manager.current_day)
                        playlists_hyb_1, best_history_patterns = other_methods.get_hyb_1_recommendations(listening_history_filtered, periods,prefix_name, listening_history_manager.current_day)
                        other_methods_playlists = other_methods.create_playlists_dict(playlists_rec_1, playlists_rec_2, playlists_hyb_1, best_history_patterns, prefix_name)
                        all_playlists = {**our_method_playlists, **other_methods_playlists}
                        #step2.create_playlists(all_playlists)
                        results = evaluation.retrieve_results()
                        if all_playlists:
                            evaluation.compute_playlist_pattern_distances(all_playlists)
                        else:
                            print("No new generated playlists found")

                        results = evaluation.retrieve_results()
                        evaluation.generate_spreadsheet(results)
                    else:
                        print(f"No history patterns found for hour {listening_history_manager.current_hour} on day {listening_history_manager.current_day}")
            else:
                 print(f"No valid clusterings produced for hour {listening_history_manager.current_hour}")
        else:
            print(f"No listening history detected for hour {listening_history_manager.current_hour}")
    else:
        print(f"No habits detected for hour {listening_history_manager.current_hour}")

if __name__ == "__main__":
    main()