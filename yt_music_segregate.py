from ytmusicapi import YTMusic
import threading
import queue
from artist_origin_checker import classify_artist

ytmusic_songs = []
transformed_songs = {
    "hindi": [],
    "non_hindi": [],
    "unknown": []
}
data_queue = queue.Queue()


def extract_songs(ytmusic):
    """Fetch liked songs from YouTube Music"""
    
    print("Fetching liked songs...\n")
    liked_songs = ytmusic.get_liked_songs(limit=1000)
    print("Fetched!\n")    
    return liked_songs


def create_chunks(liked_songs):
    for i in range(0, len(liked_songs['tracks']), 100):
        chunk = liked_songs['tracks'][i:i + 100]
        yield chunk


def trasform_songs(liked_songs):
    """Segregate songs based on artist origin (Hindi, Non-Hindi, Unknown)"""
    
    for songs in create_chunks(liked_songs):
        for song in songs:
            print(song['artists'][0]['name'].split(', ')[0], "\n")
            result = classify_artist(song['artists'][0]['name'].split(', ')[0])
            
            if result.get('is_indian') == True:
                transformed_songs["hindi"].append(song.get('videoId'))
            elif result.get('is_indian') == False:
                transformed_songs["non_hindi"].append(song.get('videoId'))
            elif result.get('is_indian') == None:
                transformed_songs["unknown"].append(song.get('videoId'))
        
            data_queue.put(transformed_songs)
            total = len(transformed_songs["hindi"]) + len(transformed_songs["non_hindi"]) + len(transformed_songs["unknown"])
            print(len(transformed_songs["hindi"]), len(transformed_songs["non_hindi"]), len(transformed_songs["unknown"]), total, len(liked_songs['tracks']), "\n")



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

    return hindi_playlist, non_hindi_playlist, unknown_songs_playlist

def load_songs_to_playlist(playlist_id, video_ids, ytmusic, genre):
    video_ids = data_queue.get()  # Wait for transformed songs to be available
    video_ids_list = video_ids[genre]
    CHUNK_SIZE = 100

    for i in range(0, len(video_ids_list), CHUNK_SIZE):
        print(f"adding {len(video_ids_list[i:i + CHUNK_SIZE])} songs to {genre} playlist...\n")
        ytmusic.add_playlist_items(playlist_id, video_ids_list[i:i + CHUNK_SIZE])
        # time.sleep(1)  # sleep to avoid rate limits


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

    # Load songs to respective playlists in parallel
    transform_thread = threading.Thread(target=transformed_songs, args=(ytmusic_songs,))
    load_hindi_thread = threading.Thread(target=load_songs_to_playlist, args=(hindi_playlist['id'], transformed_songs["hindi"], ytmusic, "Hindi"))
    load_non_hindi_thread = threading.Thread(target=load_songs_to_playlist, args=(non_hindi_playlist['id'], transformed_songs["non_hindi"], ytmusic, "Non-Hindi"))
    load_unknown_thread = threading.Thread(target=load_songs_to_playlist, args=(unknown_songs_playlist['id'], transformed_songs["unknown"], ytmusic, "Unknown"))

    # Start threads
    transform_thread.start()
    load_hindi_thread.start()
    load_non_hindi_thread.start()
    load_unknown_thread.start()

    # Wait for all threads to complete
    transform_thread.join() 
    load_hindi_thread.join()
    load_non_hindi_thread.join()
    load_unknown_thread.join()

    print("Done!")


if __name__ == "__main__":
    main()
