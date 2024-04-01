from step1 import csv_to_dict, compute_periods
from step2 import compute_listening_history_patterns
import os

directory_name = "listening_histories"


def print_pattern(pattern):
    for song in pattern:
        print(f"Name: {song['trackName']}, Timestamp: {song['endTime']}")
    print("\n")

def print_listening_history_patterns(listening_history_patterns):
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

def main():
    with open("data/longest_patterns.txt", "w") as file:
        for listening_history_file in os.listdir(directory_name):
            listening_history_file_path = os.path.join(directory_name, listening_history_file)
            listening_history_file_data = csv_to_dict(listening_history_file_path)
            if listening_history_file_data:
                periods = compute_periods(listening_history_file_data)
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


if __name__ == "__main__":
    main()