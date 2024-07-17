import step1
import step2
import listening_history_manager
import sys
from datetime import datetime

valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
valid_hours = [i for i in range(0, 24)]


def parse_arguments():
    args = sys.argv[1:]
    current_day = None
    current_hour = None
    listening_history_file = None

    for i in range(len(args)-1):
        if args[i] == "-d" and args[i+1] in valid_days:
            current_day = args[i+1]
        if args[i] == "-h" and int(args[i+1]) in valid_hours:
            current_hour = int(args[i+1])
        if args[i] == "-f":
            listening_history_file = args[i+1]

    if not current_day:
        current_day =  datetime.now().strftime("%A")
    if current_hour is None:
        current_hour = int(datetime.now().hour)
    
    return current_day, current_hour, listening_history_file


def main():
    current_day, current_hour, listening_history_file = parse_arguments()
    prefix_name = step1.compute_prefix_name(listening_history_file)

    if not listening_history_file:
        listening_history_file = input(step1.input_message)

    #listening history processing
    listening_history_file_data = None
    if listening_history_file:
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
        
    #step 1
    if not most_similar_song_sets:
        clusterings = step1.compute_clusterings(current_period_listening_history)
        if all(value == {} for value in clusterings.values()):
            sys.exit()
        clustering_song_sets = step1.generate_clustering_song_sets(clusterings)
        most_similar_song_sets = step1.compute_most_similar_song_sets(clustering_song_sets, periods, current_hour_listening_habits)
        step1.upload_most_similar_song_sets(most_similar_song_sets, prefix_name)

    timestamp_key = step2.get_timestamp_key(periods)
    history_patterns = step2.compute_best_history_patterns(periods, timestamp_key, prefix_name)

    #step 2
    optimal_solutions_indexes = step2.compute_optimal_solution_indexes(history_patterns, most_similar_song_sets)
    our_method_playlist = step2.retrieve_optimal_solution_songs(optimal_solutions_indexes, most_similar_song_sets)
    our_method_playlist = step2.create_playlists_dict(our_method_playlist, history_patterns, prefix_name, 'our_method')    
    step2.create_playlists(our_method_playlist)

if __name__ == "__main__":
    main()