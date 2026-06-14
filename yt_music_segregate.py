from ytmusicapi import YTMusic
import threading
import queue
import os
import time
import pandas as pd
from artist_origin_checker import classify_artist


ytmusic_songs = []
transformed_songs = {
    "hindi": [],
    "non_hindi": [],
    "unknown": []
}
data_queue = queue.Queue()

headers = ["artist_name", "is_indian"]

pd.DataFrame(columns=headers).to_csv(
    "artist_cache.csv",
    index=False,
    header=not os.path.exists("artist_cache.csv"),
    mode="a",
)

def extract_songs(ytmusic):
    """Fetch liked songs from YouTube Music"""
    
    print("Fetching liked songs...\n")
    liked_songs = ytmusic.get_liked_songs(limit=1000)
    print("Fetched!\n")
    time.sleep(1)    
    return liked_songs


def create_chunks(liked_songs):
    """Create chunks of songs to process in batches"""
    for i in range(0, len(liked_songs['tracks']), 100):
        chunk = liked_songs['tracks'][i:i + 100]
        yield chunk


def trasform_songs(liked_songs):
    """Segregate songs based on artist origin (Hindi, Non-Hindi, Unknown)"""
    
    for songs in create_chunks(liked_songs):
        for song in songs:
            artist = song['artists'][0]['name'].split(', ')[0]

            try:
                cache_existing_data = pd.read_csv('artist_cache.csv')
            except pd.errors.EmptyDataError as error:
                cache_existing_data = pd.DataFrame(columns=["artist_name", "is_indian"])

            print(artist, "\n")
            result_df = cache_existing_data[cache_existing_data["artist_name"] == artist]

            if result_df.empty:
                result = classify_artist(artist).get('is_indian')
                pd.DataFrame([{'artist_name': artist, 'is_indian': result}]).to_csv('artist_cache.csv', mode='a', header=False, index=False)
            else:
                result = result_df.iloc[0]['is_indian']


            if result == True:
                transformed_songs["hindi"].append(song.get('videoId'))
            elif result == False:
                transformed_songs["non_hindi"].append(song.get('videoId'))
            elif pd.isna(result):
                transformed_songs["unknown"].append(song.get('videoId'))
            # data_queue.put(transformed_songs)

            total = len(transformed_songs["hindi"]) + len(transformed_songs["non_hindi"]) + len(transformed_songs["unknown"])
            print(len(transformed_songs["hindi"]), len(transformed_songs["non_hindi"]), len(transformed_songs["unknown"]), total, len(liked_songs['tracks']), "\n")
    time.sleep(1)

def create_playlist(ytmusic):
    """Create playlists for Hindi, Non-Hindi and Unknown songs"""
    print("Creating  playlists...\n")

    try:
        hindi_playlist = ytmusic.get_playlist("PLGBSVoE5r1n_MMykSAeanNhA9vi4Dl6uY", limit=1)
        non_hindi_playlist = ytmusic.get_playlist("PLGBSVoE5r1n9-SUf9JcJjkP1eXYrnCzXx", limit=1)
        unknown_songs_playlist = ytmusic.get_playlist("PLGBSVoE5r1n89n7DXqOUtxjwOF7ZSz_Cf", limit=1)
        print("Hindi, Non Hindi and unknown songs playlist already exist\n")
    except:
        hindi_playlist = ytmusic.create_playlist(
            title="Hindi Collection",
            description="Automatically created playlist of Hindi liked songs",
            privacy_status="PRIVATE"
        )
        non_hindi_playlist = ytmusic.create_playlist(
            title="Non Hindi Collection",
            description="Automatically created playlist of Non-Hindi liked songs",
            privacy_status="PRIVATE"
        )
        unknown_songs_playlist = ytmusic.create_playlist(
            title="Unknown Songs Collection",
            description="Automatically created playlist of Unknown liked songs",
            privacy_status="PRIVATE"
        )
        print("Hindi, Non-Hindi and unknown songs playlist created\n")

    print(hindi_playlist, non_hindi_playlist, unknown_songs_playlist, "\n")
    time.sleep(1)

    return hindi_playlist, non_hindi_playlist, unknown_songs_playlist


def load_songs_to_playlist(playlist_id, video_ids, ytmusic, genre):
    # video_ids = data_queue.get()  # Wait for transformed songs to be available
    # video_ids_list = video_ids[genre]
    video_ids_list = video_ids
    CHUNK_SIZE = 10


    if len(video_ids_list) > 0:
        # ytmusic.add_playlist_items(playlist_id, video_ids_list)
        for i in range(0, len(video_ids_list), CHUNK_SIZE):
            print(f"adding {len(video_ids_list[i:i + CHUNK_SIZE])} songs to {genre} playlist {playlist_id}...\n")
            res = ytmusic.add_playlist_items(playlist_id, video_ids_list[i:i + CHUNK_SIZE])
            time.sleep(1)  # sleep to avoid rate limits


def main():
    """Main function to execute the script"""

    ytmusic = YTMusic("headers_auth.json")

    global ytmusic_songs
    ytmusic_songs = extract_songs(ytmusic)

    print(f"Total {len(ytmusic_songs['tracks'])} songs fetched...\n")

    # segregate songs based on artist origin
    trasform_songs(ytmusic_songs)

    # Create new playlists
    hindi_playlist, non_hindi_playlist, unknown_songs_playlist = create_playlist(ytmusic)
    
    load_songs_to_playlist(hindi_playlist['id'], transformed_songs["hindi"], ytmusic, "hindi")
    load_songs_to_playlist(non_hindi_playlist['id'], transformed_songs["non_hindi"], ytmusic, "non_hindi")
    load_songs_to_playlist(unknown_songs_playlist['id'], transformed_songs["unknown"], ytmusic, "unknown")

    # Load songs to respective playlists in parallel
    # try:
    #     transform_thread = threading.Thread(target=trasform_songs, args=(ytmusic_songs,))
    #     load_hindi_thread = threading.Thread(target=load_songs_to_playlist, args=(hindi_playlist['id'], transformed_songs["hindi"], ytmusic, "hindi"))
    #     load_non_hindi_thread = threading.Thread(target=load_songs_to_playlist, args=(non_hindi_playlist['id'], transformed_songs["non_hindi"], ytmusic, "non_hindi"))
    #     load_unknown_thread = threading.Thread(target=load_songs_to_playlist, args=(unknown_songs_playlist['id'], transformed_songs["unknown"], ytmusic, "unknown"))

    #     # Start threads
    #     transform_thread.start()
    #     load_hindi_thread.start()
    #     load_non_hindi_thread.start()
    #     load_unknown_thread.start()

    #     # Wait for all threads to complete
    #     transform_thread.join() 
    #     load_hindi_thread.join()
    #     load_non_hindi_thread.join()
    #     load_unknown_thread.join()
    # except Exception as e:
    #     breakpoint()
    #     print(f"Error occurred: {e}")
    #     exit(1)
    print("Done!")


if __name__ == "__main__":
    main()
