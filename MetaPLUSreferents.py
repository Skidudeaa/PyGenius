
import requests
from textwrap import shorten

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

def get_song_details(song_id, api_key):
    url = f"https://api.genius.com/songs/{song_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    song_details = response.json()['response']['song']
    return song_details

def get_referents_and_annotations(song_id, api_key, limit=10, max_length=400):
    url = f"https://api.genius.com/referents?song_id={song_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    referents = response.json()['response']['referents']
    
    # Separate verified artist annotations and community annotations
    verified_annotations = [r for r in referents if r['annotations'][0]['verified']]
    community_annotations = [r for r in referents if not r['annotations'][0]['verified']]
    
    # Combine and sort by votes, then take the top 'limit' annotations
    top_referents = sorted(verified_annotations + community_annotations, key=lambda x: x['annotations'][0]['votes_total'], reverse=True)[:limit]
    
    return top_referents

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

def main():
    max_length = 400  # Define the maximum length for annotations
    api_key = "6IJtS4Xta8IPcEPwmC-8YVOXf5Eoc4RHwbhWINDbzomMcFVXQVxbVQapsFxzKewr" # Replace with your API key
    search_term = input("Enter the song: ")
    song_id = get_song_id(search_term, api_key)
    song_details = get_song_details(song_id, api_key)
    referents = get_referents_and_annotations(song_id, api_key)

    with open("referents_and_annotations.txt", "w", encoding="utf-8") as file:
        # Write referents and annotations to file
        file.write("Top Referents and Annotations:\n")
        for referent in referents:
            file.write(f"Referent: {referent['fragment']}\n")
            annotation_text = referent['annotations'][0]['body']['dom']['children']
            annotation_text_str = extract_text(annotation_text)
            annotation_text_short = shorten(annotation_text_str, width=max_length, placeholder="...")
            file.write(f"Annotation: {annotation_text_short}\n")
            file.write("---\n")
    
    #print("Referents and annotations have been saved to 'referents_and_annotations.txt'.")

    print("Song Description:", song_details['description']['dom']['children'][0]['children'][0])
    #print("Historical Context:", song_details.get('custom_performances', []))
    print("\nSong Title:")
    print(song_details['title'])    
    print("\nArtist Name:")
    print(song_details['primary_artist']['name'])
    print("\nAlbum Name:")
    print(song_details['album']['name'])
    print("\nRelease Date:")
    print(song_details['release_date'])
    print("\nSong Art Image:")
    print(song_details['song_art_image_url'])
    print("\nPage Views:")
    print(song_details['stats']['pageviews'])

    print("\nHistorical Context:")
    for context in song_details.get('custom_performances', []):
        label = context['label']
        artists = ", ".join([artist['name'] for artist in context['artists']])
        print(f"{label}: {artists}")

    print("Top Referents and Annotations:")
    for referent in referents:
        print("Referent:", referent['fragment'])
        annotation_text = referent['annotations'][0]['body']['dom']['children']
        # Extract the annotation text
        annotation_text_str = extract_text(annotation_text)
        # Shorten the annotation if it's too long
        annotation_text_short = shorten(annotation_text_str, width=max_length, placeholder="...")
        print("Annotation:", annotation_text_short)
        print("---")


if __name__ == "__main__":
    main()




'''
    print("\nSong Description:")
    print(song_details['description']['dom']['children'][0]['children'][0])

    print("\nHistorical Context:")
    for context in song_details.get('custom_performances', []):
        label = context['label']
        artists = ", ".join([artist['name'] for artist in context['artists']])
        print(f"{label}: {artists}")

    print("\nTop Referents and Annotations:")
    for referent in referents:
        print("\nReferent:", referent['fragment'])
        annotation_text = referent['annotations'][0]['body']['dom']['children'][0]['children'][0]
        # Shorten the annotation if it's too long
        annotation_text_short = shorten(annotation_text, width=max_length, placeholder="500")
        print("Annotation:", annotation_text_short)
        print("---")
'''


