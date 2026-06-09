from typing import Dict, List, Optional, Tuple

Song = Dict[str, object]
PlaylistMap = Dict[str, List[Song]]

DEFAULT_PROFILE = {
    "name": "Default",
    "hype_min_energy": 7,
    "chill_max_energy": 3,
    "favorite_genre": "rock",
    "include_mixed": True,
}


def normalize_title(title: str) -> str:
    """Normalize a song title for comparisons."""
    if not isinstance(title, str):
        return ""
    return title.strip()  # Keep original capitalization


def normalize_artist(artist: str) -> str:
    """Normalize an artist name for comparisons."""
    if not artist:
        return ""
    return artist.strip()  # Keep original capitalization


def normalize_genre(genre: str) -> str:
    """Normalize a genre name for comparisons."""
    return genre.lower().strip()


def normalize_song(raw: Song) -> Song:
    """Return a normalized song dict with expected keys."""
    title = normalize_title(str(raw.get("title", "")))
    artist = normalize_artist(str(raw.get("artist", "")))
    genre = normalize_genre(str(raw.get("genre", "")))
    energy = raw.get("energy", 5)

    if isinstance(energy, str):
        try:
            energy = int(energy)
        except ValueError:
            energy = 5

    # Clamp energy to valid range (1-10)
    if not isinstance(energy, int) or energy < 1 or energy > 10:
        energy = 5

    tags = raw.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    return {
        "title": title,
        "artist": artist,
        "genre": genre,
        "energy": energy,
        "tags": tags,
    }


def classify_song(song: Song, profile: Dict[str, object]) -> List[str]:
    """Return a list of mood labels given a song and user profile."""
    energy = song.get("energy", 0)
    genre = song.get("genre", "")
    title = song.get("title", "")

    hype_min_energy = profile.get("hype_min_energy", 7)
    chill_max_energy = profile.get("chill_max_energy", 3)
    favorite_genre = profile.get("favorite_genre", "")

    hype_keywords = ["rock", "punk", "party"]
    chill_keywords = ["lofi", "ambient", "sleep"]

    is_hype_keyword = any(k in genre for k in hype_keywords)
    is_chill_keyword = any(k in title for k in chill_keywords)

    moods = []
    
    # Hype: energy >= hype_min_energy AND (favorite genre or hype keywords)
    if energy >= hype_min_energy and (genre == favorite_genre or is_hype_keyword):
        moods.append("Hype")
    
    # Chill: energy <= chill_max_energy OR title contains chill keywords
    if energy <= chill_max_energy or is_chill_keyword:
        moods.append("Chill")
    
    # Mixed: any song that doesn't meet Hype or Chill criteria
    if not moods:
        moods.append("Mixed")
    
    return moods


def build_playlists(songs: List[Song], profile: Dict[str, object]) -> PlaylistMap:
    """Group songs into playlists based on mood and profile."""
    playlists: PlaylistMap = {
        "Hype": [],
        "Chill": [],
        "Mixed": [],
    }

    for song in songs:
        normalized = normalize_song(song)
        moods = classify_song(normalized, profile)
        if moods:  # Only add if song matches favorite genre
            normalized["mood"] = moods[0]  # Store primary mood for display
            for mood in moods:
                playlists[mood].append(normalized)

    return playlists


def merge_playlists(a: PlaylistMap, b: PlaylistMap) -> PlaylistMap:
    """Merge two playlist maps into a new map."""
    merged: PlaylistMap = {}
    for key in set(list(a.keys()) + list(b.keys())):
        merged[key] = a.get(key, [])
        merged[key].extend(b.get(key, []))
    return merged


def compute_playlist_stats(playlists):
    """
    Compute statistics based on UNIQUE songs across all playlists.
    
    Args:
        playlists: Dictionary with keys like "Hype", "Chill", "Mixed"
    
    Returns:
        Dictionary with total_songs, hype_count, chill_count, mixed_count,
        hype_ratio, avg_energy, top_artist, top_artist_count
    """
    # Use a dictionary to track unique songs (key = title|artist)
    unique_songs = {}
    
    # Track songs by mood for counting
    hype_songs = set()
    chill_songs = set()
    mixed_songs = set()
    
    # Process each playlist
    for mood, songs in playlists.items():
        for song in songs:
            # Create unique key (case-insensitive to avoid duplicates)
            song_key = f"{song['title'].lower()}|{song['artist'].lower()}"
            
            # Store the song if we haven't seen it before
            if song_key not in unique_songs:
                unique_songs[song_key] = song
            
            # Track which playlists contain this song (for mood counting)
            if mood == "Hype":
                hype_songs.add(song_key)
            elif mood == "Chill":
                chill_songs.add(song_key)
            elif mood == "Mixed":
                mixed_songs.add(song_key)
    
    total_songs = len(unique_songs)
    hype_count = len(hype_songs)
    chill_count = len(chill_songs)
    mixed_count = len(mixed_songs)
    
    # Calculate hype ratio (percentage of hype songs relative to total)
    hype_ratio = (hype_count / total_songs * 100) if total_songs > 0 else 0
    
    # Calculate average energy across all unique songs
    total_energy = sum(song.get('energy', 0) for song in unique_songs.values())
    avg_energy = total_energy / total_songs if total_songs > 0 else 0
    
    # Find top artist (most songs by the same artist)
    artist_counts = {}
    for song in unique_songs.values():
        artist = song.get('artist', 'Unknown')
        artist_counts[artist] = artist_counts.get(artist, 0) + 1
    
    top_artist = None
    top_artist_count = 0
    if artist_counts:
        top_artist = max(artist_counts, key=artist_counts.get)
        top_artist_count = artist_counts[top_artist]
    
    return {
        "total_songs": total_songs,
        "hype_count": hype_count,
        "chill_count": chill_count,
        "mixed_count": mixed_count,
        "hype_ratio": hype_ratio,
        "avg_energy": avg_energy,
        "top_artist": top_artist,
        "top_artist_count": top_artist_count,
    }


def most_common_artist(songs: List[Song]) -> Tuple[str, int]:
    """Return the most common artist and count."""
    counts: Dict[str, int] = {}
    for song in songs:
        artist = str(song.get("artist", ""))
        if not artist:
            continue
        counts[artist] = counts.get(artist, 0) + 1

    if not counts:
        return "", 0

    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return items[0]


def search_songs(
    songs: List[Song],
    query: str,
    field: str = "artist",
) -> List[Song]:
    """Return songs matching the query on a given field (case-insensitive, partial match)."""
    if not query:
        return songs

    q = query.lower().strip()
    filtered: List[Song] = []

    for song in songs:
        value = str(song.get(field, "")).lower()
        if value and q in value:
            filtered.append(song)

    return filtered


def lucky_pick(
    playlists: PlaylistMap,
    mode: str = "any",
) -> Optional[Song]:
    """Pick a song from the playlists according to mode."""
    if mode == "hype":
        songs = playlists.get("Hype", [])
    elif mode == "chill":
        songs = playlists.get("Chill", [])
    else:
        songs = playlists.get("Hype", []) + playlists.get("Chill", [])

    return random_choice_or_none(songs)


def random_choice_or_none(songs: List[Song]) -> Optional[Song]:
    """Return a random song or None."""
    import random

    return random.choice(songs)


def history_summary(history: List[Song]) -> Dict[str, int]:
    """Return a summary of moods seen in the history."""
    counts = {"Hype": 0, "Chill": 0, "Mixed": 0}
    for song in history:
        mood = song.get("mood", "Mixed")
        if mood not in counts:
            counts["Mixed"] += 1
        else:
            counts[mood] += 1
    return counts

def add_new_song_pipeline(
    new_song: Song, 
    all_songs: List[Song], 
    profile: Dict[str, object]
) -> Tuple[List[Song], PlaylistMap, Dict[str, object]]:
    """
    Pure functional pipeline to inject a song and recalculate metrics instantly.
    
    Returns:
        tuple: (updated_songs_list, updated_playlists, live_stats)
    """
    # 1. Add the raw song to the collection copy to maintain purity
    updated_songs = all_songs + [new_song]
    
    # 2. Rebuild playlists from the complete list of songs
    updated_playlists = build_playlists(updated_songs, profile)
    
    # 3. Compute the freshly updated stats dictionary
    live_stats = compute_playlist_stats(updated_playlists)
    
    return updated_songs, updated_playlists, live_stats