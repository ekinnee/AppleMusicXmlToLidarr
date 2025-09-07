# AppleMusicXmlToLidarr

Export your Apple Music Library to the default xml and feed it to this. It looks up the MusicBrainz ID for the given track and write that to a JSON file for import into Lidarr.

## Usage

### Initial Processing
Convert Apple Music Library XML to Lidarr JSON format:

```bash
python3 AppleMusicXmlToLidarr.py Library.xml found_tracks.json not_found_tracks.json
```

This will:
- Parse your Apple Music Library.xml file
- Look up MusicBrainz IDs for each track
- Save found MBIDs to `found_tracks.json` for Lidarr import
- Save unmatched tracks to `not_found_tracks.json` for later processing

### Recheck Mode
Reprocess tracks that were not found initially:

```bash
python3 AppleMusicXmlToLidarr.py --recheck found_tracks.json not_found_tracks.json
```

This will:
- Read tracks from `not_found_tracks.json`
- Search for MusicBrainz IDs for each track again
- Append any newly found MBIDs to the existing `found_tracks.json`
- Update `not_found_tracks.json` by removing successfully matched tracks

### Workflow

1. Run initial processing to generate both found and not-found files
2. Import the found tracks into Lidarr
3. Periodically run recheck mode to find MBIDs for previously unmatched tracks
4. Import any newly found tracks into Lidarr

The recheck mode is useful because:
- MusicBrainz database is constantly updated with new entries
- Network issues may have caused temporary lookup failures
- You can refine your approach or wait for better data coverage

## Output Files

- **found_tracks.json**: Contains MusicBrainz IDs in Lidarr-compatible format
- **not_found_tracks.json**: Contains track metadata for songs that couldn't be matched

Both files use UTF-8 encoding and pretty-printed JSON for readability.
