import requests
import time
from textwrap import shorten
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from io import BytesIO
from PIL import Image
#from time import sleep
from typing import Optional
from fuzzywuzzy import fuzz



# Class to fetch lyrics from Musixmatch
class LRCProvider:
    USER_TOKEN = "190523f77464fba06fa5f82a9bfab0aa9dc201244ecf5124a06d95"
    SEARCH_ENDPOINT = "https://apic-desktop.musixmatch.com/ws/1.1/track.search?format=json&q={q}&page_size=5&page=1&s_track_rating=desc&quorum_factor=1.0&app_id=web-desktop-app-v1.0&usertoken={token}"
    LRC_ENDPOINT = "https://apic-desktop.musixmatch.com/ws/1.1/track.subtitle.get?format=json&track_id={track_id}&subtitle_format=lrc&app_id=web-desktop-app-v1.0&usertoken={token}"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Pythonista/4.0 Mobile/15E148 Safari/605.1"
            }
        )

    def search_save_parse_lrc(self, search_term: str, lrc_save_path: str, parsed_save_path: str) -> Optional[str]:
        url = self.SEARCH_ENDPOINT.format(q=search_term, token=self.USER_TOKEN)
        r = self.session.get(url)
        if not r.ok:
            print("Search failed.")
            return
        body = r.json()["message"]["body"]
        if not body or not body["track_list"] or len(body["track_list"]) == 0:
        #if not body:
            print("No tracks found.")
            return
        track_id = body["track_list"][0]["track"]["track_id"]
        url = self.LRC_ENDPOINT.format(track_id=track_id, token=self.USER_TOKEN)
        r = self.session.get(url)
        if not r.ok:
            print("Failed to get LRC.")
            return
        lrc_text = r.json()["message"]["body"]["subtitle"]["subtitle_body"]
        with open(lrc_save_path, 'w', encoding="utf-8") as file:  # Specify UTF-8 encoding here
            file.write(lrc_text)
        #lrc_text = r.json()["message"]["body"]["subtitle"]["subtitle_body"]
        #print("Raw LRC Text:")
        #print(lrc_text)
        
        lines = lrc_text.strip().split('\n')
        timestamps = []
        lyrics = []
        for line in lines:
            if line.startswith('['):
                timestamp_str, lyric = line.split(']', 1)
                timestamp_str = timestamp_str[1:]
                minutes, seconds = map(float, timestamp_str.split(':'))
                timestamp = minutes * 60 + seconds
                timestamps.append(timestamp)
                lyrics.append(lyric)
        with open(parsed_save_path, 'w', encoding='utf-8') as file:
            for timestamp, lyric in zip(timestamps, lyrics):
                file.write(f"{timestamp}: {lyric}\n")
        #for time, lyric in zip(timestamps, lyrics):
            #print(f"{time}: {lyric}")

def get_song_id(search_term, api_key):
    url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"q": search_term}
    response = requests.get(url, headers=headers, params=params)
    response_json = response.json()
    
    if 'response' not in response_json or 'hits' not in response_json['response'] or not response_json['response']['hits']:
        print(f"No results found for '{search_term}'. Please try again with a different search term.")
        exit()

    song_id = response_json['response']['hits'][0]['result']['id']
    return song_id

def get_referents_and_annotations(song_id, api_key, limit=12, max_length=400):
    url = f"https://api.genius.com/referents?song_id={song_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    referents = response.json()['response']['referents']
    
    # Separate verified artist annotations and community annotations
    verified_annotations = [r for r in referents if r['annotations'][0]['verified']]
    community_annotations = [r for r in referents if not r['annotations'][0]['verified']]
    
    # Combine and sort by votes, then take the top 'limit' annotations
    top_referents = sorted(verified_annotations + community_annotations, key=lambda x: x['annotations'][0]['votes_total'], reverse=True)[:limit]
    
    # Extract referents and annotations
    extracted_referents = []
    for referent in top_referents:
        fragment = referent['fragment']
        annotation_text = referent['annotations'][0]['body']['dom']['children']
        annotation_text_str = extract_text(annotation_text)
        annotation_text_short = shorten(annotation_text_str, width=max_length, placeholder="...")
        extracted_referents.append((fragment, annotation_text_short))
        
    # Save referents and annotations to file
    with open("referents_and_annotations.txt", "w", encoding="utf-8") as file:
        for fragment, annotation_text_short in extracted_referents:
            file.write(f"Referent: {fragment}\n")
            file.write(f"Annotation: {annotation_text_short}\n")
            file.write("---\n")
        
    return extracted_referents

def extract_text(content, depth=0):
    if depth > 10:  # Prevent infinite recursion
        return ''
    
    # If content is a dictionary, extract the children
    if isinstance(content, dict):
        children = content.get('children', [])
    # If content is a list, use it directly
    elif isinstance(content, list):
        children = content
    else:
        # If content is neither a dictionary nor a list, return an empty string
        return ''
    
    return ''.join([extract_text(child, depth + 1) if isinstance(child, (dict, list)) else str(child) if isinstance(child, (str, int, float)) else '' for child in children])

def read_lyrics(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lyrics_data = file.readlines()
    return [(float(line.split(":")[0]), line.split(":")[1].strip()) for line in lyrics_data if line.strip()]

import re

def normalize_text(text):
    text = text.lower()  # Convert to lowercase
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove all punctuation
    return text.strip()  # Remove leading and trailing whitespace

#hard to get lyrcis and ref's to agree they are the same, so it won't display the annotations
'''def map_referents_to_lyrics(lyrics, referents):
    referent_map = []
    for ref_text, annotation in referents:
        ref_text_normalized = normalize_text(ref_text)
        found = False
        for time_stamp, line_lyric in lyrics:
            line_lyric_normalized = normalize_text(line_lyric)
            if ref_text_normalized in line_lyric_normalized:
                referent_map.append((time_stamp, line_lyric, annotation))
                found = True
                break
        if not found:
            print(f"Referent not found in lyrics: {ref_text}")
    return referent_map
'''
def jaccard_similarity(str1, str2):
    set1 = set(str1.lower().split())
    set2 = set(str2.lower().split())
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union) if union else 0

def map_referents_to_lyrics(lyrics, referents):
    referent_map = []
    for ref_text, annotation in referents:
        best_match_index = -1
        best_similarity = -1
        for i, (_, line_lyric) in enumerate(lyrics):
            similarity = fuzz.partial_ratio(ref_text, line_lyric)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_index = i
        
        if best_similarity > 40:  # Adjust the threshold as needed
            time_stamp, line_lyric = lyrics[best_match_index]
            referent_map.append((time_stamp, line_lyric, annotation))
        else:
            print(f"Referent not found in lyrics: {ref_text}")
    return referent_map

#def map ref working 8-22
'''
def map_referents_to_lyrics(lyrics, referents):
    referent_map = []
    for ref_text, annotation in referents:
        best_match_index = -1
        best_similarity = -1
        for i, (_, line_lyric) in enumerate(lyrics):
            similarity = jaccard_similarity(ref_text, line_lyric)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_index = i
        
        if best_similarity > 0.09: # Threshold for similarity
            time_stamp, line_lyric = lyrics[best_match_index]
            referent_map.append((time_stamp, line_lyric, annotation))
        else:
            print(f"Referent not found in lyrics: {ref_text}")
    #print("Referent map:", referent_map)  # Debug print
    return referent_map
'''
'''
def get_album_cover_art(song_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    song_url = f'https://api.genius.com/songs/{song_id}'
    song_response = requests.get(song_url, headers=headers)
    if song_response.status_code == 200:
        song_details = song_response.json()
        album = song_details.get('response', {}).get('song', {}).get('album')
        if album:
            cover_art_url = album.get('cover_art_url')
            return cover_art_url
    return None
'''

def get_album_artwork_url(song_id, api_key):
    url = f"https://api.genius.com/songs/{song_id}"  # Modify this URL if necessary
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    response_json = response.json()
    artwork_url = response_json['response']['song']['album']['cover_art_url']
    return artwork_url

'''
def display_background_image(url):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    plt.imshow(img)
    plt.axis('off') # Turn off axis
'''

def main():
    # Define file paths and API key
    lyrics_file_path = 'parsed_synced_lyrics.txt'
    lrc_save_path = "Sync.lyrics.lrc"
    api_key = "VQczCgvrz62h4e09JVCyQfi8XD1QOCSgyqcGS_Yaob9VndXFl-YF4DuOAu3m3ByA"

    # Fetch song details, referents, and annotations
    search_term = input("Enter the song: ")
    provider = LRCProvider()
    provider.search_save_parse_lrc(search_term, lrc_save_path, lyrics_file_path)
    song_id = get_song_id(search_term, api_key)
    referents = get_referents_and_annotations(song_id, api_key)
    # Read the lyrics from the file
    lyrics = read_lyrics(lyrics_file_path)

    # Map the referents to the corresponding lyrics lines and timestamps
    referent_map = map_referents_to_lyrics(lyrics, referents)

    song_id = get_song_id(search_term, api_key)
    
    '''
    # Get album artwork URL
    artwork_url = get_album_artwork_url(song_id, api_key)
    
    # Display album artwork
    img = mpimg.imread(artwork_url)
    plt.imshow(img)
    plt.axis('off')  # Turn off axes
    plt.show(block=False)  # Display image without blocking t he rest of the code
    '''

    # Merge lyrics and annotations into a single list
    playback_list = [(timestamp, lyric, "lyric") for timestamp, lyric in lyrics]
    playback_list += [(timestamp, annotation, "annotation") for timestamp, _, annotation in referent_map]
    playback_list.sort(key=lambda x: x[0])  # Sort by timestamp

    # Iterate through the playback list, displaying content in sync with timestamps
    for i in range(len(playback_list) - 1):
        timestamp, content, content_type = playback_list[i]
        next_timestamp, _, _ = playback_list[i + 1]

        # Print content based on its type
        if content_type == "lyric":
            print(content)  # Display the lyric line
        else:
            print("Annotation:", content)  # Display the annotation

        # Wait for the duration until the next line
        sleep_time = next_timestamp - timestamp
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Print the last content item
    print(playback_list[-1][1] if playback_list[-1][2] == "lyric" else "Annotation: " + playback_list[-1][1])

    print("Song playback complete.")

if __name__ == "__main__":
    main()
