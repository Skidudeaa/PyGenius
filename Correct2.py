import requests
import json
import sys

def get_referent_details(song_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://api.genius.com/referents?song_id={song_id}'
    response = requests.get(url, headers=headers)
    referents_details = response.json()
    print(response.status_code)

    with open('referents_details.json', 'w') as file:
        json.dump(referents_details, file)

    print("Referents details saved to 'referents_details.json'")

    # ... rest of the code for filtering and printing referents ...

def filter_referents(referents, min_length=50, max_length=700, top_n=10, max_verified=6):
    # Separate verified and unverified referents
    verified_referents = [r for r in referents if r['annotations'][0]['verified']]
    unverified_referents = [r for r in referents if not r['annotations'][0]['verified']]
    sorted_unverified = sorted(unverified_referents, key=lambda x: x['annotations'][0]['votes_total'], reverse=True)
    filtered_unverified = [r for r in sorted_unverified if min_length <= len(r['fragment']) <= max_length][:top_n]
    filtered_verified = verified_referents[:max_verified]
    filtered_referents = filtered_verified + filtered_unverified
    return filtered_referents

if __name__ == "__main__":
    access_token = '0n6Kl19XCMCFr-K2ozFFoqvVDHk6yyMSMUWH9L9fj6yaFQz2Qsr8UuP3QknJQiC2'
    song_id = sys.argv[1] if len(sys.argv) > 1 else '3359190'
    get_referent_details(song_id, access_token)

    with open('referents_details.json') as file:
        referents_details = json.load(file)

    referents = referents_details['response']['referents']
    filtered_referents = filter_referents(referents)

    def extract_text_from_children(children):
        texts = []
        for child in children:
            if isinstance(child, str):
                texts.append(child)
            elif isinstance(child, dict):
                if child['tag'] == 'p':
                    texts.extend(extract_text_from_children(child['children']))
        return texts

    # Print details of filtered referents
    for i, referent in enumerate(filtered_referents):
        fragment = referent['fragment']
        votes_total = referent['annotations'][0]['votes_total']
        verified = referent['annotations'][0]['verified']

        # Extract annotation text using recursive function
        annotation_text = ' '.join(extract_text_from_children(referent['annotations'][0]['body']['dom']['children']))

        print(f"Referent {i + 1}:")
        print(f"  Fragment: {fragment}")
        print(f"  Votes Total: {votes_total}")
        print(f"  Verified: {verified}")
        print(f"  Annotation: {annotation_text}\n")
