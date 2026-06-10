# Orthography adaptation proposal: aynu-itah ← Sakaguchi (阪口諒) conventions

Review-gated proposal for mkpoli, 2026-06-10. Evidence: Sakaguchi 2024 dissertation +
2020 -ahcin article (normalized lines), vs. the 2,918 lemmas in
`/home/mkpoli/projects/Ainu/aynu-itah/src/lib/data.json` (grep counts below run against it).
Nothing here is applied; each item ends with a recommendation + migration note.

## 1. Vowel length: double-vowel spelling (the user's seed example: *raanu-*)

- **Sakaguchi**: long vowels always written with doubled vowel letters in the phonemic
  line: *raanup, cookay, nee, teere, ruura, tehpoo, yooponi, yuuturu, uurara, kaani,
  weepekere*. Piłsudski's acute accent regularly corresponds to a long vowel
  (*inránu* → *raanu-*, *jóboni* → *yooponi*, Cyrillic *ю́туру* → *yuuturu*).
- **Ours**: same convention in principle (aaca, iine, weepekere, otakaa…), **but
  inconsistently applied**: 147 lemma groups differ only in vowel length, many of them
  true doublets of one word: `tekoro/teekoro`, `urara/uurara`, `okakara/okaakara`,
  `ranneno/ranneeno`, `konte/kontee`, `manu/manuu`, `eki/ekii`, `weepekere/wepekere`,
  `tara/taraa/taara`, `caca/caaca`, `kay/kaay/kaaay`, `ponopono` (Sakaguchi:
  *poonopoono*), `kunee` (Sakaguchi: *kuune*), `kaari` (Sakaguchi: *kari*).
- **Delta**: not a convention change but an **audit**: fix length per primary-source
  evidence (Piłsudski accents, katakana 長音, Murasaki/Hattori transcriptions) and merge
  doublets, recording the loser as a variant/form.
- **Affected**: ~147 doublet groups (≈300 lemmas) + unknown number of singletons with
  wrong length (e.g. `ponopono`, `kunee`).
- **Recommendation**: adopt Sakaguchi's normalizations as the default arbiter for
  Sakhalin items he treats; migrate doublets into one entry with `forms`. Length
  conflicts inside Sakaguchi (e.g. *tehpoo* 2020 vs *tehpo* diss. ch.7-8) resolved
  toward the explicitly argued form (here *tehpoo*, 山邊 1913: 127).

## 2. Nasal before p: morphophonemic m/n (mp vs np)

- **Sakaguchi**: writes the underlying nasal: *sampe* (sam-pe), *humpa*, *sarampa*,
  *tampaku*, *rukumpa* (rukum-pa) with **mp**; but *ninpa* (nin-pa), *anpa*, *punpa*,
  *yuppa* keep **n** where the root ends in n.
- **Ours**: mostly blanket **np**: `sanpe`, `hunpa`, `saranpa`, `tanpaku`, `ninpa`,
  `anpa` (95 lemmas contain *np*); 10 lemmas contain *mp* (`humpe`, `kampi`,
  `hempah(no)`, `hekempa`, `rampo`…) — i.e. the dataset is already split.
- **Delta**: choose per-morpheme: m-final roots written with m (sampe, humpa, rukumpa,
  sarampa, tampaku, humpe), n-final roots with n (ninpa, anpa, punpa).
- **Affected**: audit all 105 np/mp lemmas; expect ~10–20 actual respellings
  (`sanpe→sampe`, `hunpa→humpa`, `saranpa→sarampa`, `tanpaku→tampaku`, …).
- **Recommendation**: adopt. Keep the np spelling as a searchable variant. Note
  Sakaguchi prints *conpay* (loan) with np — loans follow source shape.

## 3. Scope of '=' (clitic boundary)

- **Sakaguchi**: '=' is reserved for the **plural clitics** AHCI (=ahci/=ahsi/=hci/
  =hsi/=ci/=si/=ahte) and AHCIN (=ahcin/=hcin/=cin/=sin); **person affixes are
  hyphenated** (an-, ku-, eci-, -an, -as), as are derivational/possessive suffixes.
- **Ours (decided)**: '=' for personal & postpositional clitics (ku=, an=, =an, =ta,
  =un) — 17 such lemmas exist (`an=`, `=an`, `i=`, `in=`, `eci=`, `=hci`, `=ci`,
  `=anahci`…) — and '-' for derivational/valency/possessive affixes.
- **Delta**: (a) keep our '=' for person clitics (deliberate divergence from Sakaguchi —
  document the mapping `ku= ⇄ ku-` for citation purposes); (b) **align with Sakaguchi on
  the plural clitics**: they are clitics, so they should uniformly be `=ahci`, `=ahcin`
  etc. Currently the dataset mixes `-ahci` (sfx, freq 39), bare `hcin` (sfx), `=hci`,
  `=ci`, `=anahci`, plus **262 lemmas that fuse the clitic into the headword**
  (`isamahci`, `ukahci`, `uynahci`, `setahahcin`, `woonekahci`…).
- **Affected**: 5 affix entries to unify; 262 fused lemmas to (eventually) demote to
  `forms` of their bases (precedent already in data: `wooneka` has form `woonekahci`
  with analysis `=hci COLL`).
- **Recommendation**: standardize affix headwords to `=ahci` / `=ahcin` (with allomorph
  list), keep `-ahci`/`hcin` as redirects; migrate fused plurals into `forms` blocks
  incrementally.

## 4. Coda neutralization: -h headwords + recorded resurfacing stem

- **Sakaguchi**: surface h written in citation/preconsonantal position (*itah, ceh, oh,
  raanu[h], sukuh, sipoh*); the underlying stop is shown via square-bracket restorations
  (*raanu[h]*, *sipo[h]*, *u[h]*) or starred stems (*\*raanup, \*uk, \*ek, \*asip,
  \*makap*), and resurfaces before vowel-initial clitics (*tup=ahci, makap=ahsi,
  rikip=asi*).
- **Ours (decided)**: citation form with -h as headword; resurfacing stem (-p/-t/-k)
  recorded separately. The data largely conforms (yuh, teh, mah, cuh) **but** 18 lemma
  groups duplicate surface/underlying pairs as separate entries: `itah/itak`,
  `oh/ok/op`, `cuh/cup`, `tuh/tup`, `sineh/sinep`, `ceh/cep`, `mih/mik`, `yahka/yakka`,
  `pahno/pakno`, `pateh/patek`, `sah/sak`, `tah/tap`, `koh/kot`, `neh/nep`, `yah/yak`,
  `reh/rep`, `roh/rok`.
- **Delta**: structural, not orthographic: keep -h headword, fold the stop-final twin
  into a `stem`/`forms` field (e.g. `raanuh`, stem `raanup-`).
- **Affected**: 18 doublet groups (~38 lemmas) + new entries from this batch (raanuh,
  usah, sukuh, eimeh, sipoh…).
- **Recommendation**: adopt; add a `stem` field to the schema so *raanuh : raanup-*
  is machine-readable (matches gen.ts validation needs).

## 5. Accent marks: none in lemmas

- **Sakaguchi**: source-orthography accents (Piłsudski *inránu*, Cyrillic stress) are
  **never carried into the normalized line**; accent is cited only as lexical
  information in prose (e.g. Sakhalin *hosíki*, 知里 1973[1942]: 469, diss. fn29).
- **Ours**: 3 lemmas carry acute accents: `rékoro`, `yay’iráykire`, `renkáyne`
  (the last duplicating plain `renkayne`).
- **Delta**: strip accents from lemmas; keep accent info (if wanted) in a dedicated
  field.
- **Affected**: 3 lemmas (1 merge).
- **Recommendation**: adopt — trivial migration.

## 6. Glottal stop / apostrophe

- **Sakaguchi**: /ʼ/ omitted unless needed; apostrophe used between vowel-final
  pronoun stem and the plural element (*anokay’ahsin*) and in incorporation
  boundaries (*kamuy’uyna-an*); parenthesized epenthetic glide as alternative
  (*anokay-(y)ahcin*).
- **Ours**: apostrophe used lexically in ~40 lemmas (`ne'an`, `ku'ani`, `u'aare`,
  `kiroro'an`, `iine'ahsuy`…), straight `'` not `’`.
- **Delta**: conventions compatible; ours is more liberal. Only normalization needed:
  one apostrophe character (recommend straight `'`), and decide `anokayahcin` vs
  `anokay'ahcin` for the new pronoun entries (candidates file uses unapostrophized
  `anokayahcin`, matching existing `eciokayahcin`).
- **Affected**: ~40 lemmas (character normalization only; `yay’iráykire` uses ’).
- **Recommendation**: keep; document. No mass change.

## 7. Bracket restorations and starred forms (citation practice, not lemmas)

- **Sakaguchi**: `[ ]` restores segments absent in the source (*pay[e]-as, sir[i]hi,
  okak[e]*); `( )` marks optional/variable segments (*anoka(y), -(y)an*); `*` marks
  unattested/reconstructed shapes (*\*raanup, \*ku-e-*); `<` shows underlying form
  (*yay-mon(<mom)-te*); two-line source-vs-normalized presentation throughout.
- **Ours**: lemmas are plain strings; no such apparatus.
- **Delta**: adopt these **only inside** `attestedForms[].form/analysis` strings (as
  already done in `sakaguchi_candidates.json`), never in `lemma`.
- **Affected**: 0 existing entries.
- **Recommendation**: adopt as documentation convention for provenance fields.

## 8. Capitalized morpheme cover-labels (AHCI, AHCIN, AN-series, CI-series, KU-series)

- **Sakaguchi**: uses small-caps/capital labels for marker families abstracting over
  allomorphs and dialect shapes.
- **Ours**: no equivalent; affix entries are concrete strings.
- **Delta**: use the cover labels in grammar prose and in `sakaguchi_paradigm.json`
  (done), keeping concrete allomorphs as dictionary entries.
- **Recommendation**: adopt for documentation; no data migration.

## Priority order for migration

1. (cheap, mechanical) §5 accents, §6 apostrophe normalization.
2. (high value) §1 vowel-length audit of the 147 doublet groups — start with pairs where
   Sakaguchi or a primary source decides the length.
3. (high value) §4 stem field + merge of the 18 coda doublet groups (raanuh model).
4. (medium) §3 plural-clitic unification (=ahci/=ahcin), then incremental demotion of
   the 262 fused-plural lemmas into forms.
5. (medium) §2 mp/np respelling audit (~105 lemmas to inspect).
