"""Ainu lexeme bank — a source-independent 語彙素 (lexeme) layer.

Two-layer design, modelled on UniDic's lexeme/word-form split:

* **Morpheme bank** (``morpheme_db``) — the atoms. Each morpheme has a
  source-independent id (form + sense). Free morphemes can head a lexeme on
  their own; bound morphemes only ever appear inside a lexeme.
* **Lexeme bank** (this package) — the canonical descriptive units that a
  human looks a word up by. Each lexeme carries a citation form, POS, glosses,
  and a ``morphemes`` composition pointing into the morpheme bank.

Every dictionary in ``ainu-dictionaries`` is then annotated through a
**crosswalk**: one row per source entry, carrying the lexeme id it maps to plus
the surface form / dialect / confidence as that source recorded it. Pivoting on
a lexeme id yields every dialect's recording of the same word — i.e. the
dialectal variation falls out of the join.
"""
