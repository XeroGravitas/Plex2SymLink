import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import csv
from collections import Counter

def generate_audit_log(input_xml, output_txt):
    # Open output file natively in UTF-8
    with open(output_txt, 'w', encoding='utf-8') as out_file:
        first = True
        
        # iterparse streams the XML without loading the whole file into RAM
        context = ET.iterparse(input_xml, events=('end',))
        
        for event, elem in context:
            if elem.tag == 'Video':
                movie_title = elem.get('title')
                year = elem.get('year')
                title_sort = elem.get('titleSort')
                original_title = elem.get('originalTitle')
                added_at = elem.get('addedAt')
                view_count = elem.get('viewCount')
                last_viewed_at = elem.get('lastViewedAt')

                imdb_id = tmdb_id = tvdb_id = None
                main_guid = elem.get('guid', '')
                
                # 1. Fallback for legacy Plex agents (e.g., com.plexapp.agents.themoviedb://11548?lang=en)
                if main_guid.startswith('com.plexapp.agents.'):
                    if 'themoviedb://' in main_guid:
                        tmdb_id = main_guid.split('://')[1].split('?')[0]
                    elif 'imdb://' in main_guid:
                        imdb_id = main_guid.split('://')[1].split('?')[0]
                    elif 'thetvdb://' in main_guid:
                        tvdb_id = main_guid.split('://')[1].split('?')[0]
                
                # 2. Modern Plex agents (plex://) using child Guid tags
                if not (imdb_id or tmdb_id or tvdb_id):
                    all_guids = elem.findall('.//Guid') + elem.findall('.//guid')
                    for g in all_guids:
                        guid_str = g.get('id')
                        if guid_str:
                            if guid_str.startswith('imdb://'):
                                imdb_id = guid_str.split('://')[1]
                            elif guid_str.startswith('tmdb://'):
                                tmdb_id = guid_str.split('://')[1]
                            elif guid_str.startswith('tvdb://'):
                                tvdb_id = guid_str.split('://')[1]
                
                # Defensive type casting for timestamps
                added_at_date = None
                if added_at and added_at.lstrip('-').isdigit():
                    added_at_date = datetime.fromtimestamp(int(added_at), timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    
                last_viewed_date = None
                if last_viewed_at and last_viewed_at.lstrip('-').isdigit():
                    last_viewed_date = datetime.fromtimestamp(int(last_viewed_at), timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

                collection_elements = elem.findall(".//Collection")
                collection_tags = [col.get('tag') for col in collection_elements if col.get('tag')]
                collections = ", ".join(collection_tags) if collection_tags else None

                # Find ALL file parts under this video entry across all <Media> tags
                part_elements = elem.findall(".//Part")
                
                for part in part_elements:
                    file_path = part.get('file') if part is not None else "No file path"

                    if not first:
                        out_file.write("\n")
                    first = False

                    # Write entry to audit log per file path
                    out_file.write(f"Movie Title: {movie_title}\n")
                    if year:
                        out_file.write(f"  Year: {year}\n")
                    if imdb_id:
                        out_file.write(f"  IMDB ID: {imdb_id}\n")
                    if tmdb_id:
                        out_file.write(f"  TMDB ID: {tmdb_id}\n")
                    if tvdb_id:
                        out_file.write(f"  TVDB ID: {tvdb_id}\n")
                    if title_sort:
                        out_file.write(f"  TitleSort: {title_sort}\n")
                    if original_title:
                        out_file.write(f"  OriginalTitle: {original_title}\n")
                    if added_at_date:
                        out_file.write(f"  AddedAt: {added_at_date}\n")
                    if last_viewed_date:
                        out_file.write(f"  LastViewedAt: {last_viewed_date}\n")
                    if view_count:
                        out_file.write(f"  ViewCount: {view_count}\n")
                    if collections:
                        out_file.write(f"  Collections: {collections}\n")
                    out_file.write(f"  File Path: {file_path}\n")

                # Clear element to free memory
                elem.clear()

def parse_movies_to_csv(input_path, output_path):
    movies = []
    current_movie = {}
    all_keys = set()

    # 1. Read the text file and parse into dictionaries
    with open(input_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            
            if not line:
                if current_movie:
                    movies.append(current_movie)
                    current_movie = {}
            elif ': ' in line:
                key, value = line.split(': ', 1)
                current_movie[key] = value
                all_keys.add(key)
        
        if current_movie:
            movies.append(current_movie)

    # 2. Count the occurrences of each title
    title_counts = Counter(movie.get('Movie Title') for movie in movies if 'Movie Title' in movie)

    # 3. Add the 'Title Count' field to every movie record
    for movie in movies:
        title = movie.get('Movie Title')
        movie['Title Count'] = title_counts.get(title, 0)
    
    all_keys.add('Title Count')

    # 4. Define the column order, placing 'Title Count' next to 'Movie Title'
    preferred_order = ["Movie Title", "Title Count", "Year", "IMDB ID", "TMDB ID", "TVDB ID", "AddedAt", "File Path"]
    headers = [key for key in preferred_order if key in all_keys]
    headers.extend([key for key in all_keys if key not in headers])

    # 5. Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(movies)

if __name__ == "__main__":
    generate_audit_log('metadata.xml', 'audit_log.txt')
    parse_movies_to_csv('audit_log.txt', 'audit_log.csv')