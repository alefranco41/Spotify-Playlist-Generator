import step1
import step2
import other_methods
import listening_history_manager
import evaluation
import sys
from datetime import datetime

valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
valid_hours = [i for i in range(0, 24)]


def parse_arguments():
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
    

    return current_day, current_hour, listening_history_file, step2, skip_existing_playlists


def main():
    current_day, current_hour, listening_history_file, force_step2, skip = parse_arguments()
    playlists = evaluation.retrieve_playlists()
    prefix_name = step1.compute_prefix_name(listening_history_file)

    our_method_playlist = playlists.get((prefix_name,current_day,current_hour,"our_method"), None)
    playlist_rec_1 = playlists.get((prefix_name,current_day,current_hour,"rec-1"), None)
    playlist_rec_2 = playlists.get((prefix_name,current_day,current_hour,"rec-2"), None)
    playlist_hyb_1 = playlists.get((prefix_name,current_day,current_hour,"hyb-1"), None)

    
    if skip and playlist_rec_1 and playlist_rec_2 and playlist_hyb_1 and our_method_playlist:
        print(f"Playlists already found for day {current_day} and hour {current_hour}")
        sys.exit()

    if not listening_history_file:
        listening_history_file = input(step1.input_message)

    
    #listening history processing
    listening_history_file_data = listening_history_manager.csv_to_dict(listening_history_file)
    periods = step1.compute_periods(listening_history_file_data, prefix_name)
    listening_history = step1.compute_listening_history(periods, prefix_name)
    listening_habits = step1.compute_listening_habits(periods, prefix_name)


    current_hour_listening_habits = {period:listening_habits.get(period, None) for period in [current_hour]}
    current_period_listening_history = {(day,hour):songs for (day,hour), songs in listening_history.items() if hour == current_hour and day == current_day}
    if not current_hour_listening_habits:
        print(f"No listening habits detected for period {(current_day,current_hour)}")
        sys.exit()
        
    if not current_period_listening_history:
        print(f"No listening history detected for period {(current_day,current_hour)}")
        sys.exit()
    
    most_similar_song_sets = step1.retrieve_most_similar_song_set(prefix_name, current_day, current_hour)
    
    ans = None
    if most_similar_song_sets and not force_step2:
        ans = input(f"A file containing the most similar song set for period {(current_day,current_hour)} has been found, would you like to skip to step 2? (y/n): ")
        if ans != 'y':
            most_similar_song_sets = None
    elif most_similar_song_sets and force_step2:
        ans = 'y'
        
    #step 1
    if not most_similar_song_sets or ans != 'y':
        clusterings = step1.compute_clusterings(current_period_listening_history)
        if all(value == {} for value in clusterings.values()):
            sys.exit()
        clustering_song_sets = step1.generate_clustering_song_sets(clusterings)
        most_similar_song_sets = step1.compute_most_similar_song_sets(clustering_song_sets, periods, current_hour_listening_habits)
        step1.upload_most_similar_song_sets(most_similar_song_sets, prefix_name)

    timestamp_key = step2.get_timestamp_key(periods)
    history_patterns = step2.compute_best_history_patterns(periods, timestamp_key, prefix_name)

    #step 2
    if not (skip and our_method_playlist):
        optimal_solutions_indexes = step2.compute_optimal_solution_indexes(history_patterns, most_similar_song_sets)
        our_method_playlist = step2.retrieve_optimal_solution_songs(optimal_solutions_indexes, most_similar_song_sets)
        playlist_length = len(our_method_playlist[(current_day,current_hour)])
        our_method_playlist = step2.create_playlists_dict(our_method_playlist, history_patterns, prefix_name, 'our_method')
    else:
        playlist_length = len(our_method_playlist[0])
        our_method_playlist = step2.create_playlists_dict({(current_day,current_hour):our_method_playlist[0]}, history_patterns, prefix_name, 'our_method')
        
    step2.create_playlists(our_method_playlist)
    

    #other methods
    if not (skip and playlist_rec_1):
        playlist_rec_1 = other_methods.get_rec_1_recommendations(current_period_listening_history,playlist_length)
        playlist_rec_1 = step2.create_playlists_dict(playlist_rec_1, history_patterns, prefix_name, 'rec-1')
    else:
        playlist_rec_1 = step2.create_playlists_dict({(current_day,current_hour):playlist_rec_1[0]}, history_patterns, prefix_name, 'rec-1')

    if not (skip and playlist_rec_2):
        playlist_rec_2 = other_methods.get_rec_2_recommendations(current_period_listening_history,playlist_length)
        playlist_rec_2 = step2.create_playlists_dict(playlist_rec_2, history_patterns, prefix_name, 'rec-2')
    else:
        playlist_rec_2 = step2.create_playlists_dict({(current_day,current_hour):playlist_rec_2[0]}, history_patterns, prefix_name, 'rec-2')
    

    if not (skip and playlist_hyb_1):
        playlist_hyb_1 = other_methods.get_hyb_1_recommendations(current_period_listening_history, history_patterns, playlist_length)
        if playlist_hyb_1 is not None:
            playlist_hyb_1 = step2.create_playlists_dict(playlist_hyb_1, history_patterns, prefix_name, 'hyb-1')
    else:
        playlist_hyb_1 = step2.create_playlists_dict({(current_day,current_hour):playlist_hyb_1[0]}, history_patterns, prefix_name, 'hyb-1')
    
    
    #experimental phase
    all_playlists = {}
    playlists_to_merge = [playlist for playlist in [our_method_playlist, playlist_hyb_1,playlist_rec_1,playlist_rec_2] if playlist is not None]
    for playlist in playlists_to_merge:
        all_playlists.update(playlist)

    evaluation.compute_playlist_pattern_distances(all_playlists)
    results = evaluation.retrieve_results()
    evaluation.generate_spreadsheet(results)


if __name__ == "__main__":
    main()