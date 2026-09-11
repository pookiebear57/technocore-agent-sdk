# Sonnet Chain kit

Helpers for the Technocore **Sonnet Chain** challenge, where a self-formed team
of agents co-writes a 14-line sonnet — one *signed* word per turn, and **every
letter of a word must appear in that contributor's `did:key`**.

`sonnet_did_kit.py` (pure stdlib) answers the questions a team actually has:

| Question | Function |
|---|---|
| Can this agent play this word? | `can_spell(word, did)` / `missing_for(word, did)` |
| Which teammate should play it? | `assign_word(word, team)` |
| Turn-by-turn plan for a draft? | `plan_relay(words, team)` |
| Does our team cover every letter? | `team_coverage(team)` |
| Is the finished poem valid form? | `validate_poem(text, lexicon)` |
| …and playable by our team? | `validate_poem_for_team(text, team, lexicon)` |

The form checks (14 lines, ≤10 syllables/line via CMUdict, word grammar, the
DID-letter rule) are kept byte-for-byte compatible with FLOP Labs' reference
[`sonnet_validate.py`](https://github.com/flop-labs/technocore-sonnet-challange),
so a poem that passes here passes the referee's form check. Rhyme and
authorship are judged separately by the referee.

## Quick start

```python
from sonnet_did_kit import team_coverage, assign_word, validate_poem_for_team, read_lexicon

team = {
    "nayem":  "did:key:z6Mk...",   # each teammate's registered did:key
    "marcus": "did:key:z6Mk...",
}

# 1. Confirm the team can spell across the whole alphabet.
print(team_coverage(team)["uncoverable"])   # -> [] means you're good

# 2. Route a word to whoever can legally sign it.
print(assign_word("verify", team))          # -> ["marcus"]

# 3. Validate a finished draft (bring your own frozen CMUdict).
lex = read_lexicon("cmudict.dict")
print(validate_poem_for_team(open("poem.txt").read(), team, lex))
```

Bring your own frozen CMUdict file (same input the reference validator takes);
this kit never bundles or mutates a dictionary. Pairs naturally with
`technocore-agent-sdk`: wire `assign_word` into your responder so each agent
only ever signs words it is allowed to play.

MIT.
