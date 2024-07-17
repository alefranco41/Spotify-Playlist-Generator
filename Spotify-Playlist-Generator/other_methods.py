from step1 import check_listening_history_file
from step2 import compute_optimal_solution_indexes, retrieve_optimal_solution_songs
from listening_history_manager import change_credentials, feature_names_to_remove, get_recommendations, get_features
import math
import pickle


#Each song of the user’s listening history is used as input to the Spotify recommender
#system to get a similar song. Notice that since this playlist is generated song-by-song, no song-set is produced
def get_rec_1_recommendations(listening_history,playlist_length):
    print("Generating REC-1 playlists...")
    playlists = {}

    for period, songs in listening_history.items():
        playlist = []
        i = 1
        for song in songs:
            if i % 12 == 0 or i == 1:
                spotify = change_credentials()
                
            print(f"Getting REC-1 recommendation for song '{song['id']}'")
            try:
                recommendation = get_recommendations(spotify=spotify, seed_tracks=[song['id']], limit=100)
            except IndexError:
                print(f"No recommendations found for track {song['id']}")
                continue
                
            if recommendation:
                try:
                    recommendation = recommendation.get('tracks')[0]
                except IndexError:
                    pass
                else:
                    if recommendation['id'] not in list(set(playlist)):
                        playlist.append(recommendation['id'])
                        i += 1
                        print(f"Progress: {round((100 * i / playlist_length),2)}%")
                        if playlist_length == len(playlist):
                            playlists[(period[0], period[1])] = playlist
                            break
        playlists[(period[0], period[1])] = playlist

    print("REC-1 playlists generated")
    return playlists

#To provide more contextual data to the recommender system, three songs of the
#user’s listening history (the current, the previous and the next) are used as input of the
#Spotify recommender system to get a similar song. Again, since the playlist is generated
#song-by-song, no song-set is produced
def get_rec_2_recommendations(listening_history,playlist_length):
    playlists = {}

    print("Generating REC-2 playlists...")
    for period, songs in listening_history.items():
        playlist = []
        j = 1
        for i, song in enumerate(songs):
            if i == 0: 
                track_ids = [song, songs[i + 1]]
            elif i == len(songs) - 1: 
                track_ids = [songs[i - 1], song]
            else:
                track_ids = [songs[i - 1], song, songs[i + 1]]
            
            if j % 12 == 0 or j == 1:
                spotify = change_credentials()
            
            print(f"Getting REC-2 recommendation for songs {[track['id'] for track in track_ids]}")
            recommendation = get_recommendations(spotify=spotify, seed_tracks=[track['id'] for track in track_ids], limit=100)

            if recommendation:
                try:
                    recommendation = recommendation.get('tracks')[0]
                except IndexError:
                    pass
                else:
                    if recommendation['id'] not in list(set(playlist)):
                        playlist.append(recommendation['id'])
                        j += 1
                        print(f"Progress: {round((100 * j / playlist_length),2)}%")
                        if playlist_length == len(playlist):
                            playlists[(period[0], period[1])] = playlist
                            break
        playlists[(period[0], period[1])] = playlist

    print("REC-2 playlists generated")
    return playlists


#A hybrid method that uses the Spotify recommendation system to generate a pool
#of candidate songs (i.e. the song-set), and uses our dynamic programming algorithm to select
#the songs to include in the user-tailored playlist, and to sort them. The song-set is created as
#follows. Since the maximum number of songs that can be passed to the recommender is five,
#we split the listening history in blocks composed of five consecutive songs. Then, for each
#block, the recommender is asked to return a number of songs so as to have a song-set of the
#same size as that of the dynamic programming method.
def get_hyb_1_recommendations(listening_history, history_patterns, playlist_length):
    playlists = {}
    spotify = change_credentials()
    print("Generating HYB-1 playlists...")
    for period, songs in listening_history.items():
        playlist = []
        blocks = [songs[i:i+5] for i in range(0, len(songs), 5) if len(songs[i:i+5]) == 5]


        # Se il numero totale di canzoni non è un multiplo di 5, aggiungi l'ultimo blocco con le canzoni rimanenti
        if len(songs) % 5 != 0:
            blocks.append(songs[(len(songs) // 5) * 5:])

        print(f"#songs: {len(songs)}, #blocks: {len(blocks)}")
              
        rec_limit = playlist_length / len(blocks)
        if int(rec_limit) != rec_limit:
            rec_limit = math.ceil(rec_limit)
            
        length = False

        #with open("stats.txt", "a") as file:
        
        progress = 0
        for block in blocks:
            spotify=change_credentials()
            if length:
                playlists[period] = playlist
                break
            print(f"Getting HYB-1 recommendations for songs {[track['id'] for track in block]}")
            #file.write(f"Getting HYB-1 recommendations for songs {[track['id'] for track in block]}: \n")
            recommendations = get_recommendations(spotify=spotify, seed_tracks=[track['id'] for track in block], limit=100)

            if recommendations:
                recommendations = recommendations.get('tracks')
                count = 0
                for recommendation in recommendations:  
                    if recommendation['id'] not in list(set(playlist)):
                        playlist.append(recommendation['id'])
                        #file.write(f"{recommendation['id']} \n")
                        count += 1
                        progress += 1
                        print(f"Progress: {round((100 * progress / playlist_length),2)}%")
                        if playlist_length == len(playlist):
                            print(f"{playlist_length} recommendations reached")
                            length = True
                            break
                        if count == rec_limit:
                            print(f"{rec_limit} recommendations reached, skipping to next block")
                            break
        
        playlists[period] = playlist

    playlist_patterns = {}

    for period, playlist in playlists.items():

        while True:
            try:
                features = get_features(playlist,spotify)
            except Exception as e:
                print(e)
                spotify = change_credentials()
            else:
                break

        playlist_pattern_all_features = list(filter(None, features))
        playlist_pattern = [{key:value for key,value in song.items() if key not in feature_names_to_remove} for song in playlist_pattern_all_features]
        playlist_patterns[period] = playlist_pattern
        
    ordered_playlists_indexes = compute_optimal_solution_indexes(history_patterns, playlist_patterns)
    ordered_playlists = retrieve_optimal_solution_songs(ordered_playlists_indexes, playlist_patterns)

    print("HYB-1 playlists generated")
    return ordered_playlists

def create_playlists_dict(playlists_rec_1, playlists_rec_2, playlists_hyb_1, history_patterns, prefix_name, current_day):
    playlists = {}

    if not playlists_rec_1:
        print("Couldn't generate playlist with rec-1 method")
    if not playlists_rec_2:
        print("Couldn't generate playlist with rec-2 method")
    if not playlists_hyb_1:
        print("Couldn't generate playlist with hyb-1 method")

    for period, playlist in playlists_rec_1.items():
        playlists[(prefix_name,current_day,period,"rec-1")] = (playlist,history_patterns[(current_day,period)])
    
    for period, playlist in playlists_rec_2.items():
        playlists[(prefix_name,current_day,period,"rec-2")] = (playlist,history_patterns[(current_day,period)])

    for period, playlist in playlists_hyb_1.items():
        playlists[(prefix_name,current_day,period[1],"hyb-1")] = (playlist,history_patterns[period])
    
    with open("data/playlists.bin", "ab") as file:
        pickle.dump(playlists, file)

    print("Playlists uploaded on data/playlists.bin")
    
    return playlists
