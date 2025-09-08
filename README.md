# AppleMusicXmlToLidarr

Export your Apple Music Library to the default xml and feed it to this. It looks up the MusicBrainz ID for the given track and write that to a JSON file for import into Lidarr.

## Usage

### Processing Individual Tracks (Default)

#### Initial Processing
Convert Apple Music Library XML to Lidarr JSON format:

```bash
python3 AppleMusicXmlToLidarr.py Library.xml found_tracks.json not_found_tracks.json
```

This will:
- Parse your Apple Music Library.xml file
- Look up MusicBrainz IDs for each track
- Save found MBIDs to `found_tracks.json` for Lidarr import
- Save unmatched tracks to `not_found_tracks.json` for later processing

#### Recheck Mode
Reprocess tracks that were not found initially:

```bash
python3 AppleMusicXmlToLidarr.py --recheck found_tracks.json not_found_tracks.json
```

This will:
- Read tracks from `not_found_tracks.json`
- Search for MusicBrainz IDs for each track again
- Append any newly found MBIDs to the existing `found_tracks.json`
- Update `not_found_tracks.json` by removing successfully matched tracks

### Processing Albums

Extract unique albums and get release-group MBIDs:

```bash
python3 AppleMusicXmlToLidarr.py albums Library.xml albums.json albums_notfound.json
```

This will:
- Parse your Apple Music Library.xml file
- Extract unique (artist, album) pairs
- Look up MusicBrainz release-group IDs for each album
- Save found release-group MBIDs to `albums.json` for Lidarr import
- Save unmatched albums to `albums_notfound.json` for later processing

### Workflow

#### For Individual Tracks
1. Run initial processing to generate both found and not-found files
2. Import the found tracks into Lidarr
3. Periodically run recheck mode to find MBIDs for previously unmatched tracks
4. Import any newly found tracks into Lidarr

#### For Albums
1. Run album processing to generate release-group MBIDs
2. Import the found albums into Lidarr as release-groups
3. Use this approach when you want to import entire albums rather than individual tracks

The recheck mode is useful for tracks because:
- MusicBrainz database is constantly updated with new entries
- Network issues may have caused temporary lookup failures
- You can refine your approach or wait for better data coverage

### Best Practices

- **Use albums subcommand** when importing entire albums to Lidarr - this provides release-group MBIDs which are more appropriate for album-based imports
- **Use default track processing** when you need fine-grained control over individual songs
- **Always save both found and not-found files** to enable reprocessing later
- **Be mindful of MusicBrainz rate limits** - the tool includes 1-second delays between requests
- **Consider the file naming convention**: use descriptive names like `albums.json`/`albums_notfound.json` for album processing

## Output Files

### For Track Processing
- **found_tracks.json**: Contains MusicBrainz recording IDs in Lidarr-compatible format
- **not_found_tracks.json**: Contains track metadata for songs that couldn't be matched

### For Album Processing  
- **albums.json**: Contains MusicBrainz release-group IDs in Lidarr-compatible format
- **albums_notfound.json**: Contains album metadata (artist, album) for albums that couldn't be matched

All files use UTF-8 encoding and pretty-printed JSON for readability.
