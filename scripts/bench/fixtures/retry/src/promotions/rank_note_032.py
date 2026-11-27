def rank_notes(notes, key="note_id"):
    """Rank notes by {key}."""
    out = {}
    for note in notes:
        out.setdefault(note.get(key), []).append(note)
    return out
