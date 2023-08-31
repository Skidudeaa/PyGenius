

import os
import json
import sys
import requests
import time
import re
import ui
from fuzzywuzzy import fuzz
from textwrap import shorten

# Constants
USER_TOKEN = "190523f77464fba06fa5f82a9bfab0aa9dc201244ecf5124a06d95"
api_key = "VQczCgvrz62h4e09JVCyQfi8XD1QOCSgyqcGS_Yaob9VndXFl-YF4DuOAu3m3ByA"


def extract_text(content, depth=0):
    if depth > 10:  # Prevent infinite recursion
        return ''
    
    if isinstance(content, dict):
        children = content.get('children', [])
    elif isinstance(content, list):
        children = content
    else:
        return ''
    
    return ''.join([extract_text(child, depth + 1) if isinstance(child, (dict, list)) else str(child) if isinstance(child, (str, int, float)) else '' for child in children])
    

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


def get_song_id(search_term, api_key):
    url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"q": search_term}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        response_json = response.json()
        song_id = response_json['response']['hits'][0]['result']['id']
        return song_id
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def read_lyrics(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lyrics_data = file.readlines()
    return [(float(line.split(":")[0]), line.split(":")[1].strip()) for line in lyrics_data if line.strip()]


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

    def search_save_parse_lrc(self, search_term: str, lrc_save_path: str, parsed_save_path: str) -> bool:
        # Search for the track
        url = self.SEARCH_ENDPOINT.format(q=search_term, token=self.USER_TOKEN)
        try:
            r = self.session.get(url)
            r.raise_for_status()
            response_json = r.json() #added line
            print("API Response:", response_json) #added line to print json
            body = r.json()["message"]["body"]
            if not body or not body["track_list"] or len(body["track_list"]) == 0:
                print("No tracks found.")
                return False
        except requests.RequestException as e:
            print(f"Search failed: {e}")
            return False

        # Get the track ID
        track_id = body["track_list"][0]["track"]["track_id"]
        url = self.LRC_ENDPOINT.format(track_id=track_id, token=self.USER_TOKEN)
        try:
            r = self.session.get(url)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to get LRC: {e}")
            return False

        # Save the LRC text and parse it
        lrc_text = r.json()["message"]["body"]["subtitle"]["subtitle_body"]
        with open(lrc_save_path, 'w', encoding="utf-8") as file:
            file.write(lrc_text)

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
        return True


def map_referents_to_lyrics(lyrics, referents):
    referent_map = []
    unmatched_lyrics = list(lyrics) # Copy of lyrics to keep track of unmatched ones
    for ref_text, annotation in referents:
        best_similarity = -1
        best_match_index = -1
        for index, (time_stamp, line_lyric) in enumerate(unmatched_lyrics):
            similarity = fuzz.ratio(ref_text, line_lyric)  # Using FuzzyWuzzy for text matching
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_index = index
        if best_similarity > 60:  # Threshold for similarity
            referent_map.append((unmatched_lyrics[best_match_index][0], "annotation", annotation))
            unmatched_lyrics.pop(best_match_index) # Remove the matched lyric
        else:
            print(f"Referent not found in lyrics: {ref_text}")

    # Add remaining unmatched lyrics to referent_map
    for time_stamp, line_lyric in unmatched_lyrics:
        referent_map.append((time_stamp, "lyric", line_lyric))
    
    # Sort by timestamp
    referent_map.sort(key=lambda x: x[0])

    return referent_map


def on_search(sender):
    search_term = search_entry.text
    provider = LRCProvider()
    if provider.search_save_parse_lrc(search_term, 'Sync.lyrics.lrc', 'parsed_synced_lyrics.txt'):
        song_id = get_song_id(search_term, api_key)
        referents = get_referents_and_annotations(song_id, api_key) # Here you get referents
        lyrics = read_lyrics('parsed_synced_lyrics.txt')
        referent_map = map_referents_to_lyrics(lyrics, referents) # And here you pass them
        for timestamp, content_type, content in referent_map:
            if content_type == "lyric":
                lyrics_text.text += content + '\n'
            else:
                annotations_text.text += "Annotation: " + content + '\n'
    else:
        lyrics_text.text = "Failed to fetch lyrics. Please try again.\n"
        annotations_text.text = ''

'''

# ... (Previous imports and constants remain unchanged)

# UI elements
view = ui.View(frame=(0, 0, 500, 700))  # Adjusted frame size for better visibility
title_label = ui.Label(frame=(20, 20, 460, 30), text="Lyrics and Annotations Search", alignment=ui.ALIGN_CENTER)
search_label = ui.Label(frame=(20, 60, 460, 25), text="Enter the song:")
search_entry = ui.TextField(frame=(20, 95, 460, 35))
search_button = ui.Button(frame=(200, 140, 100, 35), title="Search")
status_label = ui.Label(frame=(20, 185, 460, 25), text="", alignment=ui.ALIGN_CENTER)
scroll_view = ui.ScrollView(frame=(20, 220, 460, 375))
scroll_view.content_size = (460, 800)  # Adjusted content size for scrolling

# Adjusted font sizes and positions of labels and text views
lyrics_label = ui.Label(frame=(0, 0, 460, 30), text="Lyrics:", font=("Helvetica", 18))
lyrics_text = ui.TextView(frame=(0, 30, 460, 300), editable=False, font=("Helvetica", 14))  # Adjusted height and font size
annotations_label = ui.Label(frame=(0, 340, 460, 30), text="Annotations:", font=("Helvetica", 18))  # Adjusted position and font size
annotations_text = ui.TextView(frame=(0, 370, 460, 400), editable=False, font=("Helvetica", 14))  # Adjusted height, position, and font size

# Adding subviews
view.add_subview(title_label)
view.add_subview(search_label)
view.add_subview(search_entry)
search_button.action = on_search
view.add_subview(search_button)
view.add_subview(status_label)
scroll_view.add_subview(lyrics_label)
scroll_view.add_subview(lyrics_text)
scroll_view.add_subview(annotations_label)
scroll_view.add_subview(annotations_text)
view.add_subview(scroll_view)

view.present('sheet')
'''

# ...

# UI elements
view = ui.View(frame=(0, 0, 500, 700), bg_color='lightblue')  # Added background color
title_label = ui.Label(frame=(20, 20, 460, 30), text="Lyrics and Annotations Search", alignment=ui.ALIGN_CENTER)
search_label = ui.Label(frame=(20, 60, 460, 25), text="Enter the song:")
search_entry = ui.TextField(frame=(20, 95, 460, 35))
search_button = ui.Button(frame=(200, 140, 100, 35), title="Search")
status_label = ui.Label(frame=(20, 185, 460, 25), text="", alignment=ui.ALIGN_CENTER)
scroll_view = ui.ScrollView(frame=(20, 220, 460, 375))
scroll_view.content_size = (460, 800)  # Adjusted content size for scrolling

# Adjusted font sizes and positions of labels and text views
lyrics_label = ui.Label(frame=(0, 0, 460, 30), text="Lyrics:", font=("Helvetica", 18))
lyrics_text = ui.TextView(frame=(0, 30, 460, 300), editable=False, font=("Helvetica", 14), scroll_enabled=True)  # Enabled scrolling
annotations_label = ui.Label(frame=(0, 340, 460, 30), text="Annotations:", font=("Helvetica", 18))  # Adjusted position and font size
annotations_text = ui.TextView(frame=(0, 370, 460, 400), editable=False, font=("Helvetica", 14), scroll_enabled=True)  # Enabled scrolling

# Adding subviews
view.add_subview(title_label)
view.add_subview(search_label)
view.add_subview(search_entry)
search_button.action = on_search
view.add_subview(search_button)
view.add_subview(status_label)
scroll_view.add_subview(lyrics_label)
scroll_view.add_subview(lyrics_text)
scroll_view.add_subview(annotations_label)
scroll_view.add_subview(annotations_text)
view.add_subview(scroll_view)

view.present('sheet')
