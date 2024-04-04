from step1 import csv_to_dict, compute_periods, compute_listening_history, compute_prefix_name
from step2 import compute_listening_history_patterns, compute_best_history_patterns
from listening_history_manager import change_credentials
import os

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
    
    patterns = compute_best_history_patterns(periods,"Tuesday","endTime","LH5")
    print(len(patterns[15]))


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
    with open("data/longest_patterns.txt", "w") as file:
        for listening_history_file in os.listdir(directory_name):
            listening_history_file_path = os.path.join(directory_name, listening_history_file)
            listening_history_file_data = csv_to_dict(listening_history_file_path)
            if listening_history_file_data:
                prefix_name = compute_prefix_name(listening_history_file)
                periods = compute_periods(listening_history_file_data, prefix_name, spotify)
                listening_history = compute_listening_history(periods, prefix_name, spotify)
                listening_history_patterns = compute_listening_history_patterns(periods, "endTime")
                longest_pattern = compute_longest_history_pattern(listening_history_patterns)
                file.write(f"Listening history file: {listening_history_file}\n")
                file.write(f"Longest pattern length: {len(longest_pattern[2])}\n")
                file.write(f"Day: {longest_pattern[0]}\n")
                file.write(f"Hour: {longest_pattern[1]}\n")
                for song in longest_pattern[2]:
                    file.write(f"TrackName: {song['trackName']} Timestamp: {song['endTime']}\n")
                file.write("\n")
            else:
                os.remove(listening_history_file_path)

