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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert Apple Music Library.xml to Lidarr JSON import format with not-found items exported.")
    parser.add_argument("xml_file", help="Path to Apple Music Library.xml")
    parser.add_argument("output_json", help="Output JSON file path for found items")
    parser.add_argument("not_found_json", help="Output JSON file path for not found items")
    args = parser.parse_args()
    main(args.xml_file, args.output_json, args.not_found_json)
