#!/usr/bin/env python3
import plistlib
import urllib.parse
import urllib.request
import json
import time
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)

def search_musicbrainz_recording(artist: str, title: str, album: str = None) -> str:
    """
    Query MusicBrainz for the recording MBID given artist, title, and optional album.
    Returns the MBID string, or empty string if not found.
    """
    base_url = "https://musicbrainz.org/ws/2/recording/"
    query = f'recording:"{title}" AND artist:"{artist}"'
    if album:
        query += f' AND release:"{album}"'
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
    Returns the MBID string, or empty string if not found.
    """
    base_url = "https://musicbrainz.org/ws/2/release-group/"
    query = f'release:"{album}" AND artist:"{artist}"'
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

def build_lidarr_json(songs: List[Dict]) -> (List[Dict], List[Dict]):
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
        logging.info(f"[{idx}/{len(songs)}] {song['artist']} - {song['title']} => MBID: {mbid if mbid else 'NOT FOUND'}")
        time.sleep(1)  # MusicBrainz rate limit for anonymous requests
    return found, not_found

def build_albums_json(albums: List[Dict]) -> (List[Dict], List[Dict]):
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
        logging.info(f"[{idx}/{len(albums)}] {album['artist']} - {album['album']} => MBID: {mbid if mbid else 'NOT FOUND'}")
        time.sleep(1)  # MusicBrainz rate limit for anonymous requests
    return found, not_found

def recheck_not_found(output_json: str, not_found_json: str):
    """
    Recheck items from not_found_json, append newly found MBIDs to output_json,
    and remove matched items from not_found_json.
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
        logging.info("No items to recheck in not found file.")
        return
    
    logging.info(f"Rechecking {len(not_found_items)} tracks from {not_found_json}")
    
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
    
    for idx, song in enumerate(not_found_items, 1):
        mbid = search_musicbrainz_recording(song["artist"], song["title"], song.get("album"))
        if mbid:
            newly_found.append({"MusicBrainzId": mbid})
            logging.info(f"[{idx}/{len(not_found_items)}] {song['artist']} - {song['title']} => MBID: {mbid}")
        else:
            still_not_found.append(song)
            logging.info(f"[{idx}/{len(not_found_items)}] {song['artist']} - {song['title']} => STILL NOT FOUND")
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
    logging.info(f"Updated {not_found_json} with {len(still_not_found)} remaining unmatched tracks")

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
    
    # Check if the first argument is a subcommand
    has_subcommand = len(sys.argv) > 1 and sys.argv[1] in ['tracks', 'albums']
    
    if has_subcommand:
        # Use subcommands
        parser = argparse.ArgumentParser(description="Convert Apple Music Library.xml to Lidarr JSON import format with not-found items exported.")
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Tracks subcommand
        tracks_parser = subparsers.add_parser('tracks', help='Process individual tracks (default)')
        tracks_parser.add_argument("--recheck", action="store_true", 
                            help="Recheck mode: process items from not_found_json instead of parsing XML")
        tracks_parser.add_argument("xml_file", nargs="?", help="Path to Apple Music Library.xml (not needed in recheck mode)")
        tracks_parser.add_argument("output_json", help="Output JSON file path for found items")
        tracks_parser.add_argument("not_found_json", help="Output JSON file path for not found items")
        
        # Albums subcommand  
        albums_parser = subparsers.add_parser('albums', help='Process unique albums')
        albums_parser.add_argument("xml_file", help="Path to Apple Music Library.xml")
        albums_parser.add_argument("output_json", help="Output JSON file path for found albums (default: albums.json)")
        albums_parser.add_argument("not_found_json", help="Output JSON file path for not found albums (default: albums_notfound.json)")
        
        args = parser.parse_args()
        
        # Handle subcommands
        if args.command == 'albums':
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
    else:
        # Backward compatibility: use original argument structure
        parser = argparse.ArgumentParser(description="Convert Apple Music Library.xml to Lidarr JSON import format with not-found items exported.")
        parser.add_argument("--recheck", action="store_true", 
                            help="Recheck mode: process items from not_found_json instead of parsing XML")
        parser.add_argument("xml_file", nargs="?", help="Path to Apple Music Library.xml (not needed in recheck mode)")
        parser.add_argument("output_json", help="Output JSON file path for found items")
        parser.add_argument("not_found_json", help="Output JSON file path for not found items")
        args = parser.parse_args()
        
        if args.recheck:
            if args.xml_file:
                logging.warning("XML file argument ignored in recheck mode")
            recheck_not_found(args.output_json, args.not_found_json)
        else:
            if not args.xml_file:
                parser.error("xml_file is required when not in recheck mode")
            main(args.xml_file, args.output_json, args.not_found_json)
