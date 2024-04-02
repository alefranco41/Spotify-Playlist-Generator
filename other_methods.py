from listening_history_manager import spotify
from step1 import feature_names_to_remove, check_listening_history_file, compute_listening_history
from step2 import compute_optimal_solution_indexes, retrieve_optimal_solution_songs, compute_best_history_patterns, compute_listening_history_patterns,retrieve_data, current_day
from evaluation import retrieve_playlists
import math
import pickle


#Each song of the user’s listening history is used as input to the Spotify recommender
#system to get a similar song. Notice that since this playlist is generated song-by-song, no song-set is produced
def get_rec_1_recommendations(listening_history,prefix_name,day_name):
    print("Generating REC-1 playlists...")
    playlists = {}
    for period, songs in listening_history.items():
        playlist = []
        generated_playlists = retrieve_playlists()
        generated_playlist = generated_playlists.get((prefix_name,day_name,period,"our_method"), None)
        if generated_playlist:
            playlist_length = len(generated_playlist[0])
        for song in songs:
            recommendation = spotify.recommendations(seed_tracks=[song['id']], limit=1).get('tracks')[0]
            if recommendation['id'] not in list(set(playlist)):
                playlist.append(recommendation['id'])
                if playlist_length == len(playlist):
                    playlists[period] = playlist
                    break
        playlists[period] = playlist

    print("REC-1 playlists generated")
    return playlists

#To provide more contextual data to the recommender system, three songs of the
#user’s listening history (the current, the previous and the next) are used as input of the
#Spotify recommender system to get a similar song. Again, since the playlist is generated
#song-by-song, no song-set is produced
def get_rec_2_recommendations(listening_history,prefix_name, day_name):
    playlists = {}
    print("Generating REC-2 playlists...")
    for period, songs in listening_history.items():
        playlist = []
        generated_playlists = retrieve_playlists()
        generated_playlist = generated_playlists.get((prefix_name,day_name,period,"our_method"), None)
        if generated_playlist:
            playlist_length = len(generated_playlist[0])
        for i, song in enumerate(songs):
            if i == 0: 
                track_ids = [song, songs[i + 1]]
            elif i == len(songs) - 1: 
                track_ids = [songs[i - 1], song]
            else:
                track_ids = [songs[i - 1], song, songs[i + 1]]
        
            recommendation = spotify.recommendations(seed_tracks=[track['id'] for track in track_ids], limit=1).get('tracks')[0]
            if recommendation['id'] not in list(set(playlist)):
                playlist.append(recommendation['id'])
                if playlist_length == len(playlist):
                    playlists[period] = playlist
                    break
        playlists[period] = playlist

    print("REC-2 playlists generated")
    return playlists


#A hybrid method that uses the Spotify recommendation system to generate a pool
#of candidate songs (i.e. the song-set), and uses our dynamic programming algorithm to select
#the songs to include in the user-tailored playlist, and to sort them. The song-set is created as
#follows. Since the maximum number of songs that can be passed to the recommender is five,
#we split the listening history in blocks composed of five consecutive songs. Then, for each
#block, the recommender is asked to return a number of songs so as to have a song-set of the
#same size as that of the dynamic programming method.
def get_hyb_1_recommendations(listening_history, periods, prefix_name, day_name):
    playlists = {}
    print("Generating HYB-1 playlists...")
    for period, songs in listening_history.items():
        playlist = []
        blocks = [songs[i:i+5] for i in range(0, len(songs), 5) if len(songs[i:i+5]) == 5]

        generated_playlists = retrieve_playlists()
        generated_playlist = generated_playlists.get((prefix_name,day_name,period,"our_method"), None)
        if generated_playlist:
            playlist_length = len(generated_playlist[0])

        limit = math.ceil(playlist_length / len(blocks))
        length = False

        for block in blocks:
            if length:
                playlists[period] = playlist
                break
            recommendations = spotify.recommendations(seed_tracks=[track['id'] for track in block], limit=playlist_length).get('tracks')
            for recommendation in recommendations:
                count = 0
                if recommendation['id'] not in list(set(playlist)):
                    playlist.append(recommendation['id'])
                    count += 1
                    if count == limit:
                        break
                    if playlist_length == len(playlist):
                        length = True
                        break
        playlists[period] = playlist

    playlist_patterns = {}

    for period, playlist in playlists.items():
        playlist_pattern_all_features = list(filter(None, spotify.audio_features(tracks=playlist)))
        playlist_pattern = [{key:value for key,value in song.items() if key not in feature_names_to_remove} for song in playlist_pattern_all_features]
        playlist_patterns[period] = playlist_pattern
    
    if check_listening_history_file(periods):
        timestamp_key = 'endTime'
    else:
        timestamp_key = 'played_at'
    

    history_patterns = compute_listening_history_patterns(periods, timestamp_key)
    best_history_patterns = compute_best_history_patterns(history_patterns, current_day, timestamp_key, prefix_name)
    ordered_playlists_indexes = compute_optimal_solution_indexes(best_history_patterns, playlist_patterns)
    ordered_playlists = retrieve_optimal_solution_songs(ordered_playlists_indexes, playlist_patterns)

    print("HYB-1 playlists generated")
    return ordered_playlists, best_history_patterns

def create_playlists_dict(playlists_rec_1, playlists_rec_2, playlists_hyb_1, history_patterns, prefix_name):
    playlists = {}

    for period, playlist in playlists_rec_1.items():
        playlists[(prefix_name,current_day,period,"rec-1")] = (playlist,history_patterns[period])
    
    for period, playlist in playlists_rec_2.items():
        playlists[(prefix_name,current_day,period,"rec-2")] = (playlist,history_patterns[period])

    for period, playlist in playlists_hyb_1.items():
        playlists[(prefix_name,current_day,period,"hyb-1")] = (playlist,history_patterns[period])
    
    with open("data/playlists.bin", "ab") as file:
        pickle.dump(playlists, file)

    print("Playlists uplaoded on data/playlists.bin")
    
    return playlists

def main():
    song_sets, periods, prefix_name = retrieve_data()
    if song_sets and periods:
        hours_to_generate_song_sets = list(song_sets.keys())
        listening_history = compute_listening_history(periods, prefix_name)
        listening_history_filtered = {hour:songs for hour,songs in listening_history.items() if hour in hours_to_generate_song_sets}
        if listening_history_filtered and any(len(value) != 0 for value in listening_history_filtered.values()):
            playlists_rec_1 = get_rec_1_recommendations(listening_history_filtered,prefix_name, current_day)
            playlists_rec_2 = get_rec_2_recommendations(listening_history_filtered,prefix_name, current_day)
            playlists_hyb_1, best_history_patterns = get_hyb_1_recommendations(listening_history_filtered, periods,prefix_name, current_day)

            playlists = create_playlists_dict(playlists_rec_1, playlists_rec_2, playlists_hyb_1, best_history_patterns, prefix_name)

            #create_playlists(playlists)
        else:
            print(f"No listening history detected for hours {hours_to_generate_song_sets}")
    else:
        print("No song sets retrieved from step 1")

    
if __name__ == "__main__":
    main()