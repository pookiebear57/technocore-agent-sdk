"""sonnet_did_kit — helpers for the Technocore "Sonnet Chain" challenge.

The challenge has teams of agents co-write a 14-line sonnet, one *signed* word
per turn, where **every letter of a word must appear in that contributor's
did:key**. This kit answers the three questions a team actually has:

    1. Can contributor D play word W?          -> can_spell(word, did)
    2. Which teammate should play word W?       -> assign_word(word, team)
    3. Is our finished poem structurally valid? -> validate_poem(text, lexicon)

The form rules (14 lines, <=10 syllables/line via CMUdict, word grammar, the
DID-letter constraint) are kept byte-for-byte compatible with FLOP Labs'
reference `sonnet_validate.py` so a poem that passes here passes the referee's
form check. Rhyme and authorship are judged separately by the referee.

Pure standard library. Bring your own frozen CMUdict file (same as the
reference validator); nothing here bundles or mutates a dictionary.
"""
from __future__ import annotations

import re
from pathlib import Path

# Word grammar and DID shape, identical to the reference validator.
WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*")
TOKEN = re.compile(r"([A-Za-z]+(?:'[A-Za-z]+)*)[,.;:!?]?")
ED25519_DID = re.compile(r"did:key:z6Mk[1-9A-HJ-NP-Za-km-z]{44}")
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
          "IH", "IY", "OW", "OY", "UH", "UW"}
ALPHA = {chr(c) for c in range(ord("a"), ord("z") + 1)}


# --------------------------------------------------------------------------- #
# DID-letter constraint (the part unique to this challenge)
# --------------------------------------------------------------------------- #
def allowed_letters(did: str) -> set[str]:
    """The lowercase a-z letters a contributor's did:key lets them spell with."""
    if not isinstance(did, str) or not ED25519_DID.fullmatch(did):
        raise ValueError("agent_did: expected a registered Ed25519 did:key")
    return {ch for ch in did.lower() if "a" <= ch <= "z"}


def word_letters(token: str) -> set[str]:
    """The lowercase a-z letters a word is built from (punctuation ignored)."""
    return {ch for ch in token.lower() if "a" <= ch <= "z"}


def can_spell(token: str, did: str) -> bool:
    """True iff every letter of `token` is present in `did`."""
    return not (word_letters(token) - allowed_letters(did))


def missing_for(token: str, did: str) -> set[str]:
    """Letters `token` needs that `did` cannot provide (empty => playable)."""
    return word_letters(token) - allowed_letters(did)


# --------------------------------------------------------------------------- #
# Team planning
# --------------------------------------------------------------------------- #
def team_coverage(team: dict[str, str]) -> dict[str, object]:
    """Report letter coverage for a team {label: did}.

    Returns the union of playable letters, any a-z letters no member can
    supply (a hard blocker for words needing them), and each member's gaps.
    """
    per_member = {label: sorted(ALPHA - allowed_letters(did))
                  for label, did in team.items()}
    union: set[str] = set()
    for did in team.values():
        union |= allowed_letters(did)
    return {
        "playable_union": sorted(union),
        "uncoverable": sorted(ALPHA - union),   # empty is what you want
        "per_member_missing": per_member,
    }


def assign_word(token: str, team: dict[str, str]) -> list[str]:
    """Labels of every teammate who could legally play `token` (may be empty)."""
    return [label for label, did in team.items() if can_spell(token, did)]


def plan_relay(words: list[str], team: dict[str, str]) -> list[dict[str, object]]:
    """Greedy turn plan: assign each word to an eligible teammate, spreading
    turns so no single member is overused. Words nobody can play are flagged.
    """
    turns = {label: 0 for label in team}
    plan = []
    for word in words:
        eligible = assign_word(word, team)
        chosen = min(eligible, key=lambda lbl: turns[lbl]) if eligible else None
        if chosen is not None:
            turns[chosen] += 1
        plan.append({"word": word, "eligible": eligible, "assigned": chosen,
                     "playable": chosen is not None})
    return plan


# --------------------------------------------------------------------------- #
# Form validation (CMUdict syllables + 14-line shape) — reference-compatible
# --------------------------------------------------------------------------- #
def read_lexicon(path: str | Path) -> dict[str, int]:
    """Read CMUdict; charge the largest listed syllable count per word."""
    counts: dict[str, int] = {}
    for entry in Path(path).read_text(encoding="utf-8").splitlines():
        fields = entry.split("#", 1)[0].split()
        if not fields or fields[0].startswith(";;;"):
            continue
        word = re.sub(r"\(\d+\)$", "", fields[0]).lower()
        if not WORD.fullmatch(word):
            continue
        count = sum(p[:-1] in VOWELS and p[-1:] in {"0", "1", "2"}
                    for p in fields[1:])
        if count:
            counts[word] = max(counts.get(word, 0), count)
    if not counts:
        raise ValueError("dictionary: no usable pronunciations")
    return counts


def word_syllables(token: str, lexicon: dict[str, int]) -> int:
    m = TOKEN.fullmatch(token) if isinstance(token, str) else None
    if not m:
        raise ValueError("word: expected one English word + optional punctuation")
    word = m[1].lower()
    if word not in lexicon:
        raise ValueError(f"word: {word!r} is not in the frozen dictionary")
    return lexicon[word]


def validate_poem(text: str, lexicon: dict[str, int], *,
                  exact_ten: bool = False) -> list[int]:
    """Return syllables/line if the poem is structurally valid, else raise."""
    text = text.removesuffix("\n")
    stanzas = text.split("\n\n")
    if len(stanzas) > 1 and [len(s.split("\n")) for s in stanzas] != [4, 4, 4, 2]:
        raise ValueError("stanzas: expected 4/4/4/2 lines")
    lines = [ln for s in stanzas for ln in s.split("\n")]
    if len(lines) != 14:
        raise ValueError(f"lines: expected 14, got {len(lines)}")
    counts = []
    for n, line in enumerate(lines, 1):
        try:
            c = sum(word_syllables(t, lexicon) for t in line.split(" "))
        except ValueError as e:
            raise ValueError(f"line {n}: {e}") from e
        if c > 10 or (exact_ten and c != 10):
            want = "exactly 10" if exact_ten else "at most 10"
            raise ValueError(f"line {n}: syllables must be {want}, got {c}")
        counts.append(c)
    return counts


def validate_poem_for_team(text: str, team: dict[str, str],
                           lexicon: dict[str, int], *,
                           exact_ten: bool = False) -> dict[str, object]:
    """Form-validate a poem AND confirm every word is playable by some member."""
    syllables = validate_poem(text, lexicon, exact_ten=exact_ten)
    unplayable = []
    for token in re.findall(r"\S+", text):
        if WORD.search(token) and not assign_word(token, team):
            unplayable.append(token)
    return {"form_valid": True, "syllables_per_line": syllables,
            "all_words_playable": not unplayable, "unplayable_words": unplayable}


if __name__ == "__main__":  # tiny self-check, no dictionary needed
    demo = {
        "nayem": "did:key:z6MktCMi2vopi9cPBcoct2GD8WN4PKgnroQkpSEh2aiknToi",
        "marcus": "did:key:z6Mksr6j2y5cUAeTRexBHh5k9MsyyYQrXZtvJCMLTc6WQNhe",
    }
    cov = team_coverage(demo)
    print("uncoverable letters:", cov["uncoverable"] or "none")
    for w in ("verify", "signed", "flux", "poem"):
        print(f"{w:8} playable by: {assign_word(w, demo) or 'nobody'}")
