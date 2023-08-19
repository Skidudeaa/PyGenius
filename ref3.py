import requests
import json


def get_referent_details(song_id, access_token):
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f'https://api.genius.com/referents?song_id={song_id}'

        response = requests.get(url, headers=headers)
        response.raise_for_status()  # raise an exception if the request was unsuccessful

        referents_details = response.json()

        with open('referents_details.json', 'w') as file:
            json.dump(referents_details, file)

        print("Referents details saved to 'referents_details.json'")

        if 'response' in referents_details:
            return referents_details['response']['referents']
        else:
            raise KeyError("Failed to retrieve referent details from the response")

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving referent details: {e}")
    except KeyError as e:
        print(f"KeyError: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by user.")


def filter_referents(referents, min_length=50, max_length=700, top_n=10, max_verified=6):
    try:
        # Separate verified and unverified referents
        verified_referents = []
        unverified_referents = []

        for r in referents:
          if r.get('annotations', [{}])[0].get('verified', False):
            verified_referents.append(r)
          else:
            unverified_referents.append(r)

        sorted_unverified = sorted(unverified_referents, key=lambda x: x.get('annotations', [{}])[0].get('votes_total', 0), reverse=True)

        filtered_unverified = [r for r in sorted_unverified if min_length <= len(r.get('fragment', '')) <= max_length][:top_n]
        filtered_verified = verified_referents[:max_verified]
        filtered_referents = filtered_verified + filtered_unverified
        return filtered_referents
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def extract_text_from_children(children):
    texts = []
    for child in children:
        if isinstance(child, str):
            texts.append(child)
        elif isinstance(child, dict):
            if child.get('tag') == 'p':
                texts.extend(extract_text_from_children(child.get('children', [])))
    return texts


if __name__ == "__main__":
    access_token = '0n6Kl19XCMCFr-K2ozFFoqvVDHk6yyMSMUWH9L9fj6yaFQz2Qsr8UuP3QknJQiC2'
    song_id = input("Enter song id: ")

    try:
        referents = get_referent_details(song_id, access_token)

        if referents:
            filtered_referents = filter_referents(referents)

            # Print details of filtered referents
            for i, referent in enumerate(filtered_referents):
                fragment = referent.get('fragment', '')
                votes_total = referent.get('annotations', [{}])[0].get('votes_total', 0)
                verified = referent.get('annotations', [{}])[0].get('verified', False)

                # Extract annotation text using recursive function
                annotation_text = ' '.join(
                    extract_text_from_children(referent.get('annotations', [{}])[0].get('body', {}).get('dom', {}).get(
                        'children', [])))

                print(f"Referent {i + 1}:")
                print(f"  Fragment: {fragment}")
                print(f"  Votes Total: {votes_total}")
                print(f"  Verified: {verified}")
                print(f"  Annotation: {annotation_text}\n")
        else:
            raise Exception("No referents found for the given song id")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")