#!/usr/bin/env python3
import plistlib
import urllib.parse
import urllib.request
import json
import time
import logging
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)

def colorize_red(text: str) -> str:
    """
    Add ANSI red color codes to text for terminal display.
    Returns the text wrapped in red color codes.
    """
    return f"\033[31m{text}\033[0m"

def clean_name_for_search(name: str) -> str:
    """
    Clean track or album names by removing common suffixes that may interfere with search matching.
    Removes ' - Single' and ' - EP' suffixes to improve MusicBrainz search accuracy.
    
    Args:
        name: The original track title or album name
        
    Returns:
        Cleaned name with suffixes removed
    """
    if not name:
        return name
    
    # Remove ' - Single' and ' - EP' suffixes (case-insensitive)
    suffixes_to_remove = [' - Single', ' - EP', ' - single', ' - ep']
    
    for suffix in suffixes_to_remove:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    
    return name

def search_musicbrainz_recording(artist: str, title: str, album: str = None) -> str:
    """
    Query MusicBrainz for the recording MBID given artist, title, and optional album.
    Names are preprocessed to remove common suffixes (' - Single', ' - EP') before searching
    to improve search accuracy.
    Returns the MBID string, or empty string if not found.
    """
    # Clean the title and album names to improve search matching
    clean_title = clean_name_for_search(title)
    clean_album = clean_name_for_search(album) if album else None
    
    base_url = "https://musicbrainz.org/ws/2/recording/"
    query = f'recording:"{clean_title}" AND artist:"{artist}"'
    if clean_album:
        query += f' AND release:"{clean_album}"'
    params = {
        "query": query,
        "fmt": "json",
        "limit": 1
    }
    url = base_url + "?" + urllib.parse.urlencode(params)
    headers = {
        "User-Agent": "AppleMusicXmlToLidarr/1.0 (ekinnee)"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            if "recordings" in data and data["recordings"]:
                return data["recordings"][0].get("id", "")
    except Exception as e:
        logging.warning(f"MusicBrainz lookup failed for '{artist} - {title}' ({album}): {e}")
    return ""

def search_musicbrainz_release_group(artist: str, album: str) -> str:
    """
    Query MusicBrainz for the release-group MBID given artist and album.
    Album names are preprocessed to remove common suffixes (' - Single', ' - EP') before searching
    to improve search accuracy.
    Returns the MBID string, or empty string if not found.
    """
    # Clean the album name to improve search matching
    clean_album = clean_name_for_search(album)
    
    base_url = "https://musicbrainz.org/ws/2/release-group/"
    query = f'release:"{clean_album}" AND artist:"{artist}"'
    params = {
        "query": query,
        "fmt": "json",
        "limit": 1
    }
    url = base_url + "?" + urllib.parse.urlencode(params)
    headers = {
        "User-Agent": "AppleMusicXmlToLidarr/1.0 (ekinnee)"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            if "release-groups" in data and data["release-groups"]:
                return data["release-groups"][0].get("id", "")
    except Exception as e:
        logging.warning(f"MusicBrainz release-group lookup failed for '{artist} - {album}': {e}")
    return ""

def parse_apple_music_xml(xml_path: str) -> List[Dict]:
    """
    Parse the Apple Music Library XML file and extract tracks with artist and title.
    Returns a list of dicts: {artist, title, album}
    """
    with open(xml_path, "rb") as f:
        plist = plistlib.load(f)
    tracks = plist.get("Tracks", {})
    song_list = []
    for track in tracks.values():
        artist = track.get("Artist")
        title = track.get("Name")
        album = track.get("Album")
        if artist and title:
            song_list.append({"artist": artist, "title": title, "album": album})
    return song_list

def extract_unique_albums(xml_path: str) -> List[Dict]:
    """
    Parse the Apple Music Library XML file and extract unique (artist, album) pairs.
    Returns a list of dicts: {artist, album}
    """
    with open(xml_path, "rb") as f:
        plist = plistlib.load(f)
    tracks = plist.get("Tracks", {})
    
    # Use a set to track unique combinations
    unique_albums = set()
    album_list = []
    
    for track in tracks.values():
        artist = track.get("Artist")
        album = track.get("Album")
        if artist and album:
            # Create a unique key for this artist-album combination
            unique_key = (artist, album)
            if unique_key not in unique_albums:
                unique_albums.add(unique_key)
                album_list.append({"artist": artist, "album": album})
    
    return album_list

def build_lidarr_json(songs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    For each song, lookup the MusicBrainzId and build the Lidarr-compatible dict.
    Returns two lists: found (with MBID) and not_found (for later processing).
    """
    found = []
    not_found = []
    for idx, song in enumerate(songs, 1):
        mbid = search_musicbrainz_recording(song["artist"], song["title"], song.get("album"))
        if mbid:
            found.append({"MusicBrainzId": mbid})
        else:
            not_found.append(song)
        logging.info(f"[{idx}/{len(songs)}] {song['artist']} - {song['title']} => MBID: {mbid if mbid else colorize_red('NOT FOUND')}")
        time.sleep(1)  # MusicBrainz rate limit for anonymous requests
    return found, not_found

def build_albums_json(albums: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    For each album, lookup the release-group MusicBrainzId.
    Returns two lists: found (with MBID) and not_found (for later processing).
    """
    found = []
    not_found = []
    for idx, album in enumerate(albums, 1):
        mbid = search_musicbrainz_release_group(album["artist"], album["album"])
        if mbid:
            found.append({"MusicBrainzId": mbid})
        else:
            not_found.append(album)
        logging.info(f"[{idx}/{len(albums)}] {album['artist']} - {album['album']} => MBID: {mbid if mbid else colorize_red('NOT FOUND')}")
        time.sleep(1)  # MusicBrainz rate limit for anonymous requests
    return found, not_found

def recheck_not_found_items(output_json: str, not_found_json: str, search_func, item_type: str, get_item_key):
    """
    Generic method to recheck items from not_found_json, append newly found MBIDs to output_json,
    and remove matched items from not_found_json.
    
    Args:
        output_json: Path to the output JSON file containing found MBIDs
        not_found_json: Path to the JSON file containing not found items
        search_func: Function to search for MBIDs (e.g., search_musicbrainz_recording)
        item_type: Type of items being processed (e.g., "tracks", "albums") for logging
        get_item_key: Function that takes an item and returns a string for logging
    """
    # Load existing not found items
    try:
        with open(not_found_json, "r", encoding="utf-8") as nf:
            not_found_items = json.load(nf)
    except FileNotFoundError:
        logging.error(f"Not found file does not exist: {not_found_json}")
        return
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in: {not_found_json}")
        return
    
    if not not_found_items:
        logging.info(f"No {item_type} to recheck in not found file.")
        return
    
    logging.info(f"Rechecking {len(not_found_items)} {item_type} from {not_found_json}")
    
    # Load existing found MBIDs
    existing_found = []
    try:
        with open(output_json, "r", encoding="utf-8") as f:
            existing_found = json.load(f)
    except FileNotFoundError:
        logging.info(f"Output file {output_json} not found, will create new one.")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in: {output_json}")
        return
    
    # Process each not found item
    newly_found = []
    still_not_found = []
    
    for idx, item in enumerate(not_found_items, 1):
        mbid = search_func(item)
        if mbid:
            newly_found.append({"MusicBrainzId": mbid})
            logging.info(f"[{idx}/{len(not_found_items)}] {get_item_key(item)} => MBID: {mbid}")
        else:
            still_not_found.append(item)
            logging.info(f"[{idx}/{len(not_found_items)}] {get_item_key(item)} => {colorize_red('STILL NOT FOUND')}")
        time.sleep(1)  # MusicBrainz rate limit for anonymous requests
    
    # Append newly found MBIDs to existing output JSON
    all_found = existing_found + newly_found
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_found, f, ensure_ascii=False, indent=2)
    
    # Update not found JSON with remaining items
    with open(not_found_json, "w", encoding="utf-8") as nf:
        json.dump(still_not_found, nf, ensure_ascii=False, indent=2)
    
    logging.info(f"Recheck complete: {len(newly_found)} newly found, {len(still_not_found)} still not found")
    logging.info(f"Updated {output_json} with {len(newly_found)} new MBIDs (total: {len(all_found)})")
    logging.info(f"Updated {not_found_json} with {len(still_not_found)} remaining unmatched {item_type}")

def recheck_not_found(output_json: str, not_found_json: str):
    """
    Recheck tracks from not_found_json, append newly found MBIDs to output_json,
    and remove matched items from not_found_json.
    """
    def search_track(item):
        return search_musicbrainz_recording(item["artist"], item["title"], item.get("album"))
    
    def get_track_key(item):
        return f"{item['artist']} - {item['title']}"
    
    recheck_not_found_items(output_json, not_found_json, search_track, "tracks", get_track_key)

def recheck_not_found_albums(output_json: str, not_found_json: str):
    """
    Recheck albums from not_found_json, append newly found MBIDs to output_json,
    and remove matched items from not_found_json.
    """
    def search_album(item):
        return search_musicbrainz_release_group(item["artist"], item["album"])
    
    def get_album_key(item):
        return f"{item['artist']} - {item['album']}"
    
    recheck_not_found_items(output_json, not_found_json, search_album, "albums", get_album_key)

def main(xml_path: str, output_json: str, not_found_json: str):
    """
    Parse XML, get MBIDs, write found to output JSON, not found to a separate file.
    """
    logging.info(f"Parsing Apple Music library: {xml_path}")
    songs = parse_apple_music_xml(xml_path)
    logging.info(f"Found {len(songs)} tracks.")

    found, not_found = build_lidarr_json(songs)

    # Write found MBIDs to output JSON (for Lidarr import)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False, indent=2)
    logging.info(f"Exported {len(found)} MusicBrainzIds to {output_json}")

    # Write not found items to a separate JSON file for later processing
    with open(not_found_json, "w", encoding="utf-8") as nf:
        json.dump(not_found, nf, ensure_ascii=False, indent=2)
    logging.info(f"Exported {len(not_found)} unmatched tracks to {not_found_json}")

def albums_main(xml_path: str, output_json: str, not_found_json: str):
    """
    Parse XML, extract unique albums, get release-group MBIDs, write found and not found to separate files.
    """
    logging.info(f"Parsing Apple Music library for albums: {xml_path}")
    albums = extract_unique_albums(xml_path)
    logging.info(f"Found {len(albums)} unique albums.")

    found, not_found = build_albums_json(albums)

    # Write found MBIDs to output JSON (for Lidarr import)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False, indent=2)
    logging.info(f"Exported {len(found)} release-group MusicBrainzIds to {output_json}")

    # Write not found items to a separate JSON file for later processing
    with open(not_found_json, "w", encoding="utf-8") as nf:
        json.dump(not_found, nf, ensure_ascii=False, indent=2)
    logging.info(f"Exported {len(not_found)} unmatched albums to {not_found_json}")

if __name__ == "__main__":
    import argparse
    import sys
    
    # Set up argument parser with subcommands
    parser = argparse.ArgumentParser(description="Convert Apple Music Library.xml to Lidarr JSON import format with not-found items exported.")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Tracks subcommand
    tracks_parser = subparsers.add_parser('tracks', help='Process individual tracks')
    tracks_parser.add_argument("--recheck", action="store_true", 
                        help="Recheck mode: process items from not_found_json instead of parsing XML")
    tracks_parser.add_argument("xml_file", nargs="?", help="Path to Apple Music Library.xml (not needed in recheck mode)")
    tracks_parser.add_argument("output_json", help="Output JSON file path for found items")
    tracks_parser.add_argument("not_found_json", help="Output JSON file path for not found items")
    
    # Albums subcommand  
    albums_parser = subparsers.add_parser('albums', help='Process unique albums (default)')
    albums_parser.add_argument("--recheck", action="store_true", 
                        help="Recheck mode: process albums from not_found_json instead of parsing XML")
    albums_parser.add_argument("xml_file", nargs="?", help="Path to Apple Music Library.xml (not needed in recheck mode)")
    albums_parser.add_argument("output_json", help="Output JSON file path for found albums")
    albums_parser.add_argument("not_found_json", help="Output JSON file path for not found albums")
    
    # Parse arguments, defaulting to 'albums' if no subcommand provided
    # First check if we need to add the default command
    if len(sys.argv) > 1 and sys.argv[1] not in ['tracks', 'albums', '-h', '--help']:
        # Insert 'albums' as the default command
        sys.argv.insert(1, 'albums')
    
    args = parser.parse_args()
    
    # If no subcommand was provided (only possible with no args or just help), show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Handle subcommands
    if args.command == 'albums':
        if args.recheck:
            if args.xml_file:
                logging.warning("XML file argument ignored in recheck mode")
            recheck_not_found_albums(args.output_json, args.not_found_json)
        else:
            if not args.xml_file:
                albums_parser.error("xml_file is required when not in recheck mode")
            albums_main(args.xml_file, args.output_json, args.not_found_json)
    elif args.command == 'tracks':
        if args.recheck:
            if args.xml_file:
                logging.warning("XML file argument ignored in recheck mode")
            recheck_not_found(args.output_json, args.not_found_json)
        else:
            if not args.xml_file:
                tracks_parser.error("xml_file is required when not in recheck mode")
            main(args.xml_file, args.output_json, args.not_found_json)
