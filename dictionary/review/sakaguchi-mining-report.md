# Sakaguchi (阪口諒) mining — final review bundle

Date: 2026-06-11. Review-gated: **nothing has been merged**; all three deliverables are new files, no existing files touched, nothing committed.

## 1. What was mined

Sources (pdftotext OCR, read-only, at `/home/mkpoli/projects/Ainu/ainu-grammar/articles/ocr/`):

- `2024_阪口諒_樺太アイヌ語における人称と数の標示に関する研究.pdftotext.txt` (dissertation, 9,119 lines) — main source
- `2020_阪口諒_アイヌ語樺太方言における名詞複数接尾辞ahcinの用法.pdftotext.txt`
- `2020_阪口諒_アイヌ語樺太方言におけるutaraの用法.pdftotext.txt`

Deliverables (all in `/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/input/sakhalin/`):

| File | Contents |
|---|---|
| `sakaguchi_candidates.json` | 145 lexeme candidates absent from (or mis-lemmatized in) `aynu-itah/src/lib/data.json` (2,918 entries), each with attested forms, morphological analyses, Sakaguchi-cited primary source, OCR-line provenance, confidence rating, review note |
| `sakaguchi_paradigm.json` | Consolidated person/number marker inventory (24 marker/system rows) with roles, dialect tags, sources, and a conflicts summary |
| `sakaguchi_orthography_proposal.md` | 8-point orthography adaptation proposal with per-point affected-entry counts against data.json |

Two independent audits ran: audit-1 (OCR faithfulness, 145 checked, 141 confirmed, 4 problems) and audit-2 (duplicates/consistency, 174 checked, 161 confirmed, 13 problems). Both verdicts: **needs-fixes** (all fixes are citation-level or headword-level; no fabricated forms were found).

## 2. Candidate lexemes

### 2.1 The raanu family (KEY ITEM) — worked in full

**Lemma: `raanuh` (vt) 「～を愛する」 'to love (someone)'; stem `raanup-`** (final *-p* surfaces as *-h* word-finally/preconsonantally per the Sakhalin coda rule).

| Attested form | Analysis | Primary source (via Sakaguchi 2024) |
|---|---|---|
| *inránu* → in-raanu[h] | **in=raanup** 1.O-love, 3PL.A subject: *piskan kamuy utara in-raanu[h] kusu* 「周りの神々が私を愛したので」; -p > -h before *kusu* | Piłsudski 1912 Nr.6, 14–16 (= Sato 1985: 160 ex 12); diss. ex 3-9 |
| *inránupan* → in-raanup-an | **in=raanup-an** 2PL.A>1.O 'you(pl) love me'; the -an marks 2nd-person plurality. Piłsudski (1912: 92) himself misparsed this as "instead of inranu" (*in* 'me' + *ranu* 'love'); Sakaguchi's correction: same verb, different subject person, lemma **\*raanup** | Piłsudski 1912 Nr.6, 16–17 & 36–37; diss. exx 3-22/3-23 |
| in-raanup (y)an | prohibitive w/ plural-addressee particle: *suy hankayki in-raanup (y)an* 「再び決して私を愛してはいけない」 | Piłsudski 1912 Nr.6, 36–37; diss. ex 3-23 |
| *ikòiránu* → ikoiraanu[h] | derived nominal **i-ko-i-raanu-p** 'loving (someone)' — confirms your i=ko-i-ra(a)nu-p sketch, with the final -h = underlying -p: *enciw onne ikoiraanu[h] ham utara kii* | Piłsudski 1912 Nr.24, 92–94; diss. exx 4-5/4-23 |
| ku-raanupa-hci | 1SG.A-love.PL — Sakaguchi flags it 正しくは *\*raanup* | Tangiku 2022: 353–354 ex 46 (= 村崎著・丹菊編 2013: 26); diss. ex 5-39, 表5-4 |

**Vowel-length ruling: `raanu` with long aa; `rannu` is dead.** Evidence: 0 hits for "rannu" in any of the three OCR files; *raanu/raanup* consistent at diss. l.1880, 2213, 2230, 2238, 3221, 3581, 5179; Piłsudski's acute (*inránu*) regularly corresponds to length in Sakaguchi's normalizations; independently corroborated by *raanu[h]*, *e-raanup-ihi*, *i-raanup*, *yay-ko-raanuh-kara* in the 2020 ahcin article (カレイ男とカジカ男 text). Audit-1 re-derived this independently and confirmed.

One fix applied to the entry per audit-1: the `ku-raanupa-hci` row's placeholder citation should read *Tangiku 2022: 353–354 ex 46*.

### 2.2 All 145 candidates

Status codes: **OK** = both audits passed; **FIX** = citation/loc correction needed (form itself verified); **DUP** = duplicate/variant of an existing data.json row — do not add as-is; **HEAD** = headword must be respelled to coda-h convention; **XREF** = add cross-reference to existing row before merge; **VER** = single/garbled token — verify against PDF before merge. D = Sakaguchi 2024 diss.; A20 = Sakaguchi 2020 ahcin art.; P = Piłsudski 1912 『資料』; P2 = Pilsudskij 2002 『資料２』; Y = 山邊・金田一 1913 『物語』; M = Majewicz ed. 2004; C = 知里; H = 服部; Mu = 村崎.

| Lemma | POS | Gloss | Key attested form(s) | Primary | St. |
|---|---|---|---|---|---|
| **raanuh** (stem raanup-) | vt | love s.o. | see §2.1 | P Nr.6/Nr.24; Tangiku 2022 | FIX |
| etohparusi | vt | forestall s.o. | in-etohparusi; e-i-(y)etohparusi; イネトㇹパルㇱカラ | 浦田 1998: 118-9; C n.d.: 6; 道教委 2007: 123 | FIX |
| kosisciwka | vt | send (wind/power) to | in-kosisciwka yan wa (prayer) | M: 410 | VER |
| topoci | n | shamanic spirit | ku-koh topoci utarak[e]-he | M: 410 | VER |
| utarake | n | group of (poss.) | topoci utarak[e]-he | M: 410 | DUP→`utarike` |
| wenkara | vt | defeat | inci-wenkara ciki | P Nr.19; Sato 1985 | OK |
| kemahto | n | rain of blood | kem-ahto ran kaane | P Nr.16 | OK |
| cikutakuta | vi | spill, pour down | kemahto cikutakuta | P Nr.16 | XREF→`cikutakutaha` |
| ruype | n | frozen fish | ruype kuma ohta | P Nr.17 | OK |
| kuma | n | drying pole | ruype kuma ohta | P Nr.17 | OK |
| huymampa | vt | examine | ceh huymampa | P Nr.17 | OK (mp question §4.2) |
| newana | sfp | assertive 'you see' | sahtek-as newana | P2 2; P: 165 | VER |
| hankayki | adv | never (PROH) | hankayki in-raanup (y)an | P Nr.6 | OK |
| hannahkusu | adv | never (w/ NEG) | hannahkusu … han nee nanko | P Nr.19/Nr.10 | OK |
| niitum | n | forest interior | niitum ene tehpoo hum | Y 10811-12 | OK |
| tehpoo | n | gun (loan) | tehpoo hum; tehpoo-sin; tehpo utara | Y; Y: 127 | FIX (cite 13010/130101) |
| enrum | n | cape | cis enrum sempiri-ke | Y 10811-12 | OK |
| sempiri | n | lee side | enrum sempiri-ke | Y 10811-12 | OK (mp §4.2) |
| repaa | vi | go offshore | repaa yan kaane | Y 10811-12 | OK |
| yaymomte | vt | let oneself drift | yay-mon(<mom)-te | Y 10811-12 | OK (lemma = underlying) |
| sekuma | n | mountain | sekuma nosk[i] un kamuy | P Nr.25 | OK |
| inuu | n | listening | pirika inuu e-kii | P Nr.2 | OK (check nuu) |
| piskan | adn/adv | around | piskan kamuy utara; piskani | P Nr.6; Y | OK (dict has only episkan-) |
| mahneku | n | woman | pirika mahneku ci-nee | P Nr.6/Nr.15 | XREF→`mahtekuh` (variant) |
| makanke | vt | make go inland | eci-makan-ke-he; an-e-makan-ke | P Nr.25/22 | OK (or forms-of makan) |
| samte | vt | marry off | eci-sam-te(-yan) | P Nr.25; P2 T.10 | OK (or forms-of sam) |
| itahotuye | vi | cease speaking(?) | ku-itah-otuye | M: 350 | VER (Sakaguchi's own ?) |
| koare | vt | seat upon | eci-ko-aa-re-yan | M: 350 | VER (koaare length?) |
| kourenkare | vt | provide for s.o. | eci-ko-urenka-re-yan | P Nr.25 | XREF→`urenkare` |
| sisturaynu | vi | lose one's way | sisturaynu utara | P Nr.6 | OK |
| ikoro | n | treasure, money | ikoro …; ikoro-sin | Y 17706; P Nr.23 | OK (high value) |
| tanukuran | adv/n | tonight | tanukuran | Y | OK (check ukuran) |
| uneyno | adv | likewise | uneyno | Y 16307 | OK |
| irukae | adv | for a while | irukae (~irukay?) | Y 16307 | VER (-e vs -y) |
| okankino | adv | on purpose | okankino an-mahpoo-ho=sin… | P2 T.10 | OK |
| asis | vi | go out (PL) | eci-asis; 'ariki, *makap, asis' PL-stem list (diss. l.8304) | P Nr.12 | XREF→`asin` (its PL stem; audit-2 strengthens lexeme status) |
| ucaanahtecise | n | jail | ucaanahtecise onne eci-ruura-an | Y 09305 | OK (single token) |
| wenno | adv | badly | wenno eci-kara | Y | OK |
| ueomante | vt | worry about | eci-ueomante hane an-kii no | Y 16204 | OK |
| urayki | vi | fight/duel | urayki-an; Sisam urayke utara | P Nr.12; Y | OK (i~e variants) |
| koramusiine | v | be at ease | koramusiine okay utara | P Nr.10 | VER (-siine vs -sinne) |
| anokayahcin | pron | we (dedicated 1PL) | anokay-(y)ahcin; anokay’ahsin ×102 in Y | P Nr.23; Y; H 1961: 6 | OK (high value) |
| ehawkomo | vi | lower voice(?) | utara ehawkomo kunpe | P Nr.10 | VER |
| eimeh | vt | distribute (food) | utara kam eime[h] | P2 6, 45 | VER (stem eimek-?) |
| inawpe | n | inaw | inawpe kara=hci | P Nr.5 | OK |
| orakata | n | Uilta people | Orakata orowano | P Nr.4 | OK |
| ohaciri | n | absence from home | ohaciri-ke ta | P Nr.21 | OK |
| niwkes | v/auxv | be unable | utara niwkes kunpe | P Nr.24 | OK |
| **eukoytak → eukoytah** (stem eukoytak-) | vi/vt | discuss together | eukoytak=ahci; e-ukoitak=ahci | P Nr.24/Nr.21 | HEAD + XREF→`ukoytah` |
| tomi | n | wealth | ikoro neanpe, tomi neanpe | P Nr.23 | OK |
| yaywente | n | invalid | tan yaywente an-kii | P Nr.21 | OK |
| renkani | postp | because of | eci-ramu-hu renkani | Y 04801 | OK (cf. renkayne) |
| asisne | adn/num | five (attr.) | asisne conpay; asisne kunkutu | Y | FIX (kunkuto~kunkutu quote) + XREF→`asne(h)` |
| conpay | n | shō measure (loan) | asisne conpay | Y 05004 | OK |
| ueramuokay | vi | think about e.o. | u-e-ramuokay=ahsi-hi | Y 11805-06 | OK (or forms-of) |
| ueramusinne | vi | be relieved (recip.) | u-e-ramusinne | Y 11805-06 | XREF→`eramusinne` |
| sirikuroh | vi | be dark all around | siri(~e)kuro[h] | Y 17203 | VER |
| ociw | vt | copulate with | in-ko-ociw-rusuy yan | P Nr.6 | OK |
| sissam | n | Japanese person | Sissam -utara Matsumae orowa | Y 00711 | OK |
| cekoyki | vi | catch fish | cekoyki kusu | Y 00711 | OK (check ceh/koyki) |
| usah (stem usap-) | vi | return together | onuman usap=ahte | C 1975/1954: 505 | OK (Shiranushi; dialect-tag) |
| sisnu | vi | live | sisnu=hci | C 1948: 337 | OK |
| tumi | n | war | tumi | C 1948: 337 | OK |
| paysere | n | sled rear | nuso paysere | P Nr.10 | OK |
| isinneno | adv | all together | isinneno ~ issinne(no) | P2; P; Y | OK |
| payke | vi | get up (PL) | numa/payke pair | Mu 1979 | OK |
| sospa | vt | tear (PL.O) | soso/sospa | Mu 1979: 42-3 | OK |
| rukumpa | vt | cut to pieces (PL.O) | an-rukumpa | Mu 1979; Ohnuki-Tierney 1969 | OK (mp §4.2) |
| tapu / tahpa | vt | grasp (SG.O/PL.O) | tapu/tahpa pair | Mu 1979: 42-3 | OK |
| hopenu / hopenpa | vi | be startled (SG/PL) | hopenu/hopenpa | D §7.1 | OK |
| ocipa | vt | throw | ocipa ~ ociipa | D §7.1 | OK |
| hosispa | vi | return (PL) | hosispa | P2: 22 | OK |
| ninu | vt | sew finely | ninu; ninpaninpa | H編 1964: 111 | OK |
| punpa | vt | lift (PL.O) | puni/punpa | D §7.1 | OK (n-final root, np stays) |
| yupu / yuppa | vt | tighten (SG.O/PL.O) | yupu/yuppa | D §7.1 | OK |
| kiroro | n | strength | kiroro koro | Mu 1976: 150 | OK |
| arahne | adv | at once | arahne | Mu 1976: 150 | OK |
| hoskikanne | adv | first, ahead | hoskikanne | P Nr.12/Nr.4 | OK |
| turepkara | vi | gather turep | turepkara kusu makap=ahsi | Y | OK |
| unkame | n | ogre | unkame poroono san | P2 T.9 | OK |
| neete | conj | and then | neete pon unkame utara | P2 T.9 | DUP→`neeteh` (h-less Cyrillic spelling) |
| hata | n | flag (loan) | hata hotahse(?) | Y | OK |
| tenunkoy | n | hand towel (loan) | terara tenunkoy | Y | OK |
| esuyasuya | vt | wave | esuyasuya=hsi | Y | OK |
| eramuokay | vt | think, know | an-eramuokay; eramuoka yan | Y | OK |
| pakesaran | adn/vi | impudent | pakesaran ita[h] | Y | OK |
| yuuturu | adn/n | middle of three | yuuturu (ю́туру) moromahpo | P2 T.9 | VER + XREF→`uturu` |
| epausi | vt | wear on head | epausi anpe uh te | Y | OK |
| oasi | vt/auxv | begin | kaa oasi | P Nr.13 | OK |
| esisi | vt | dodge | esisi | P Nr.4 | OK |
| raapoke | n/adv | meanwhile | raapoke ta | P Nr.4 | OK |
| yaykota | adv | by oneself | yaykota | Y | OK |
| pencay | n | junk ship (loan) | pencay an-oo=si | Y | OK |
| kotesu | vt | fit against | kotesu | Y | VER |
| enko | n | half | enko | Y | OK |
| kisarapuy | n | ear-hole | kisarapuy naa mesu=hsi | Y | OK |
| etupuy | n | nostril | etupuy naa mesu=hsi | Y | OK |
| uarikire | vi | come along together (PL) | u-ariki-re=hci | P Nr.4 | OK |
| umakahte | vi | go inland together (PL) | umakahte | D §8.2.1 | OK |
| tunakay | n | reindeer (loan) | neya tunakay utara | P Nr.4 | OK |
| ohoorono | adv | for a long time | ohoorono | Y | OK |
| aruwan | num/adn | seven (attr.) | tan cuh aruwan too | Y | OK |
| tupesan | num/adn | eight (attr.) | tupesan tanku asisne kunkutu | Y | FIX (kunkutu quote) |
| tanku | num | hundred | tupesan tanku | Y | FIX (kunkutu quote) |
| sipoh (stem sipop-?) | n | box, chest | sipo[h] oo ikoro | Y; P Nr.23 | OK |
| aciwcikah | n | falcon(?) | onnew naa aciwcikah naa | Y | VER |
| sohkan | n | sculpin | pon sohkan[a] ohkayo | P2 T.3 | VER |
| usaan | adn | various | usaan | Mu 1976: 15 | OK |
| asiste | vt | take out (PL theme) | an-asis-te | P Nr.23/Nr.17 | VER + XREF→asis |
| sapane | vi | be chief | sapane tono | Y | XREF→unglossed `sapan` (f5) |
| karauto | n | chest (loan) | karauto oo ikoro | P Nr.23 | OK |
| tusuku | n | shaman | mahneku tusuku | P Nr.15 | OK |
| onneno | postp | up to, even | hekaci onneno | P Nr.10 | OK |
| **ramat → ramah** (stem ramat-) | n | soul | mac-ihi ramat-[u]hu | P Nr.21 | HEAD + XREF→`kuhramatuhu` |
| tehpokusuri | n | gunpowder | tehpo-kusuri | Y | OK |
| eurayahte | vt | marvel at together | eurayahte | P Nr.23 | OK |
| eicaarare | vt | not believe(?) | eicaarare=si | P2 T.9 | OK (gloss ?) |
| sukuh | adn | young | sukuh ohkayo utara | Y | OK |
| yama | n | mountain (loan) | yama ohta | Y | OK |
| iriwah | n | sibling | iriwah | H編 1964 | OK |
| cinkew | n | ancestor | an-cinkew vs an-cinkew-he | Y; C 1942 | XREF→`cinkewhe`, `cinkewutarihcin` |
| kiyane | adn/vi | elder (sibling) | an-kiyane-k(uh)-utara | P Nr.27 | OK |
| sopake | n/nl | head seat | sopake-he-sin | P Nr.23 | OK |
| tukareke | n/nl | place in front of | tukareke-he-cin | P Nr.15 | XREF→unglossed `tukar` (f3) |
| haworokehe | nmlz | voice of (doing) | hawʼoroke-sin an | Y; P Nr.21 | XREF→`orokehe`, `haworo` |
| humorokehe | nmlz | sound of (doing) | humoroke(he) | Mu 1976 | XREF→`orokehe` |
| ruuorokehe | nmlz | trace of (doing) | ruuoroke(he) | Mu 1976 | XREF→`orokehe` |
| utohseka | vi | sleep all together | u-tohse-ka ruhe-sin | P | OK |
| pinaponne | adv | secretly | pinapónne u-mojmoje | P Nr.21 | OK |
| eucarare | vi | talk with one another | e-u-cara-re | P Nr.23 | VER |
| horokeu | n | wolf | tám múre horoḱéu | P Nr.23 | VER |
| sirimah (stem sirimak-) | n | guardian spirit | sirimak-i-sin | P Nr.23 | VER |
| kamesu | vt | save, protect | an-kamesu=hci | P Nr.23 | OK |
| sekuhpe | n | young man | iwan pon sekuhpe | P Nr.26 | VER |
| hopihsanne | vi/adv | away from beach | hopihsanne makap-ahsi | Y | OK |
| yaykoreske | vi | grow up on one's own | yaykoreske | P Nr.25 | VER |
| sirankore | n | relative | ay-sirankore-utara | Y | OK |
| uetorekoyki | vi | snore at each other | u-etor-e-koyki=hci | P Nr.23 | VER |
| upookoro | colloc | parent(s)+child(ren) | u-poo-koro -utah | H編 1964: 41 | OK |
| ucinkewkoro | colloc | parent and child | u-cinkew-koro -utah | H編 1964: 41 | OK |
| inci= | pers | 1.O passive prefix | inci-wenkara; inci-tuye | P Nr.19/Nr.16; Sato 1985 | OK (2 tokens; NE-Hokkaido enci-/unci- parallel) |
| yan | parti | IMP.PL particle | paye yan te; in-ko-ociw-rusuy yan | P; Y | OK |

## 3. Person/number paradigm (`sakaguchi_paradigm.json`) vs our current rows

The system (East Sakhalin, diss. Tables 3-1/3-2/7-1):

| Series | A | S | O | Pronoun | Referent in texts |
|---|---|---|---|---|---|
| KU (1SG) | ku= | ku= | **in=** | kuani | 1SG — **nom-acc** |
| CI (1PL gram.) | ci= | **=as** | **in=** | ciokay~cookay | always 《1SG》 (folktale quoted speech) — **tripartite** |
| 2SG | e= | e= | e= | eani | neutral |
| 2PL | eci= | eci= | eci= | ecioka(y) | neutral |
| 3 | ∅ | ∅ | ∅ | ani(hi) | number-neutral; animate PL via =ahci or PL stem |
| AN (4th person) | an= | =an | i= | anoka(y); dedicated 1PL anokayahcin | indefinite / passive-agent / 1SG / 1PL — **tripartite** |

Portmanteau/circumfix: eci= 1>2SG; eci=…-yan 1>2PL; in= 2SG>1; in=…-an 2PL>1 (the -(y)an marks **2nd-person** plurality); e-i- 2SG>4; eci-i- 2PL>4; an-e- 4>2SG; eci-…-(y)an 4>2PL; inci= 1st-person passive; an-i- 4>4 passive (vs Dal Corso's bare an-). Raichishka substitutes en= (KU.O) / un= (CI.O). Object affixes index the ditransitive **recipient** (secondary-object alignment).

**Corrections to our dictionary rows** (this is the reconciliation target list; audit-2 asked that it be stated explicitly):

1. **in= (f3, currently glossed "1PL?") — WRONG.** It is the 1st-person **object** prefix for BOTH KU and CI series, referent always 《1SG》 in texts (Table 7-1). Sato 1985 had it CI-only; Sakaguchi extends to KU. Merge the duplicate unglossed bare `in` row (f3).
2. **=as is MISSING from the dictionary entirely** (the task brief was wrong; only `as` 'occur' f1 exists). Add: CI-series S suffix, grammatically plural (triggers PL stems: asip-as, pay[e]-as), referent 《1SG》.
3. **a= must lose the 二人称・敬称 reading.** Sakhalin AN-series is NOT 2nd-person honorific (Hokkaido-only); the 2PL-honorific niche is filled by standalone `utara`. Unify a= with an= as allomorph; note ay= before y/s, am before m.
4. **e= gloss 君が（の） omits O**: e= is neutral S/A/O (e-reske 'raise you', an-e-anpa-re) + possessor.
5. **eci= (f46, glossed singular あなた) — wrong number**: 2PL S/A/O + possessor, AND homophonous 1>2SG portmanteau (eci-sam-te 'I marry you off'). Merge duplicate `eci` row (f6).
6. **i= = 4th-person O** (《1SG/1PL》), not generic; also kinship possessor (i-hoskiram-hu).
7. **=an / an=**: 4th person (Nakagawa 1988's term), grammatically plural (okay-an, makap-an, tup-an even for 1SG referents); =an follows auxiliaries (paye-rusuy-an), always precedes AHCI. **Logophoric note**: Tangiku 2022: 357 adds 'person in quotation' for West-coast North; Hokkaido's incl-1PL/2HON/narrative-1SG functions are absent in Sakhalin.
8. **No inclusive/exclusive anywhere in Sakhalin** (diss. fn72) — EXCL labels are comparative-Hokkaido only.
9. **AHCI fragmentation**: five rows (-ahci f39, =hci f21, hci f11, =ci f2, hcin f1) → consolidate under **=ahci** (verbal plural clitic; allomorphs =ahsi/=hci/=hsi/=ci/=si, Shiranushi =ahte, W-coast-south -sin/-cin; marks subject OR human primary-object plurality; optional) and **=ahcin** (nominal plural clitic, only on possessed forms/nominalizers, additive only) — **two distinct morphemes** per Sakaguchi (contra 知里/丹菊).
10. **Add en= row gap (audit-2)**: dict has en= (f21); the paradigm file lacks a dedicated en= row (Raichishka KU.O; also decide un= representation) — to be added from the diss Raichishka tables/服部 1961 before merge.
11. Noise rows `ki=` (f5), `ek=` (f2), `=` (f6): unaccounted; probably tokenization artifacts — investigate.

**Conflicts with the concurrent `ainu-morpheme-database/sakhalin/affixes.json`** (report-only, not edited): (a) it glosses ci=/=as/in= as 1PL.**EXCL** — contradicts fn72 (no incl/excl); (b) its =hci entry lacks the Shiranushi =ahte and W-coast-south -sin/-cin allomorphs (diss. l.4636-4641, 4075-4083); (c) inci= absent there; (d) it frames un= as Hokkaido-only, while the paradigm assigns un= (CI.O) to Raichishka — (a)–(c) are diss-verified, (d) needs a page-level PDF check.

## 4. Orthography adaptation proposal (summary; full text in `sakaguchi_orthography_proposal.md`)

| § | Point | Delta vs us | Affected | Rec. |
|---|---|---|---|---|
| 1 | Vowel length: doubled vowels (raanup, cookay, tehpoo); Piłsudski acute = length | Same convention, inconsistently applied | **~147 doublet groups (≈300 lemmas)** (tekoro/teekoro, urara/uurara, ponopono→poonopoono, kunee→kuune…) | Audit + merge, Sakaguchi as arbiter for items he treats |
| 2 | Morphophonemic nasal: **mp** for m-final roots (sampe, humpa, sarampa), **np** for n-final (ninpa, anpa, punpa) | We use blanket np (95 np vs 10 mp lemmas) | audit 105; ~10–20 respellings | Adopt; keep np as variant; loans (conpay) keep source shape |
| 3 | '=' scope: Sakaguchi reserves = for AHCI/AHCIN; we keep = for person clitics (deliberate divergence, document ku= ⇄ ku-) but align on plural clitics =ahci/=ahcin | 5 affix entries to unify + **262 fused-plural lemmas** (isamahci, setahahcin…) to demote to forms | 267 | Adopt =ahci/=ahcin headwords; incremental demotion |
| 4 | Coda: -h headword + recorded stem (raanuh : raanup-) | 18 surface/underlying doublet groups (itah/itak, ceh/cep, cuh/cup…) | ~38 lemmas + new batch | Adopt; add machine-readable `stem` field to schema |
| 5 | No accents in lemmas | 3 lemmas (rékoro, yay’iráykire, renkáyne dup) | 3 (1 merge) | Adopt, trivial |
| 6 | Apostrophe: compatible; normalize character to `'` | ~40 lemmas | char-normalization only | Keep ours; document |
| 7 | [ ]/( )/*/ < citation apparatus | provenance fields only, never lemmas | 0 | Adopt as documentation convention |
| 8 | Cover labels (AHCI, KU-series…) | prose/paradigm only | 0 | Adopt for docs |

Migration priority: §5+§6 (cheap) → §1 length audit → §4 stem field + 18 merges → §3 clitic unification → §2 mp/np audit.

## 5. Audit flags — drop or double-check

**Citation fixes (forms themselves verified):**
- `raanuh`: replace placeholder cite on ku-raanupa-hci with *Tangiku 2022: 353–354 ex 46 (= 村崎著・丹菊編 2013: 26)*.
- `etohparusi`: fn28 ↔ fn30 articleLocs swapped (知里 n.d. quote is fn30 l.2102-2104; 道教委 2007 is fn28 l.2098-2099); optionally add ex 3-18 (浦田 1998: 118-119).
- `tehpoo`: OCR prints 『物語』130101 (6 digits) at ex 8-19 — check PDF for 13010 / 13010-1 / 13010-13011.
- `asisne/tanku/tupesan`: shared quote reads kunkut**o** at ex 7-34 but kunkut**u** at ex 8-21 — verify in PDF, or cite only ex 8-21.

**Do not add as new entries (duplicates):** `utarake` (= a-vowel variant of existing `utarike`; diss fn122 itself equates -utarike = -utari + -ke), `neete` (= existing `neeteh`).

**Respell headwords to coda-h convention:** `ramat` → **ramah** (stem ramat-), `eukoytak` → **eukoytah** (stem eukoytak-).

**Hold pending PDF/source check (all single or garbled tokens):** kosisciwka, topoci, newana, itahotuye, koare, irukae, koramusiine (-siine vs -sinne), ehawkomo, eimeh, sirikuroh, kotesu, aciwcikah, sohkan, asiste, yuuturu (vs `uturu` — y-epenthesis question), eucarare, horokeu, sekuhpe, sirimah, yaykoreske, uetorekoyki.

**Cross-references to add before merge:** cinkew→cinkewhe; sapane→sapan; tukareke→tukar; haworokehe/humorokehe/ruuorokehe→orokehe/haworo; asis→asin; mahneku→mahtekuh; ueramusinne→eramusinne; kourenkare→urenkare; cikutakuta→cikutakutaha.

**Paradigm-internal gloss slips in the diss itself (cite carefully):** okay-an=ahsi tagged 4.A at ex 5-2 (should be 4.S); e-oman tagged 行く.PL at ex 7-11 (oman is SG); e-koro glossed 2SG.S in 2020 ex 4-24 (koro is vt); eaykah/easkay glosses apparently swapped at diss. l.4234-4238 — verify in PDF.

## 6. Recommended next actions

1. **Merge first (clean, multi-token, high value)** into `new_terms`: raanuh (with fixed cite), ikoro, piskan, hankayki, hannahkusu, sekuma, niwkes, tomi, mahneku, sissam, tusuku, sukuh, tehpoo, the numerals (asisne, aruwan, tupesan, tanku), the SG/PL verb pairs (tapu/tahpa, yupu/yuppa, soso→sospa, payke, hopenu/hopenpa, punpa), anokayahcin, inci=, yan, ohaciri, okankino, hoskikanne, urayki, etohparusi (with fixed locs), wenkara, usah, sisnu.
2. **Merge after the two headword fixes**: ramah, eukoytah.
3. **Hold**: everything in the VER list above + the four DUP/variant items (route those as `forms`/variants of the existing rows instead).
4. **Personal rows in data.json**: apply the §3 reconciliation map — fix in=, add =as, fix eci=/e=/a= glosses, consolidate the five AHCI rows, add the en=/un= Raichishka row to the paradigm first, investigate ki=/ek=/=.
5. **affixes.json** (concurrent build): drop EXCL labels on ci=/=as/in=; add =ahte and -sin/-cin allomorphs to =hci; add inci=; page-check the un= Raichishka claim.
6. **lemmatize.py**: teach it (a) coda alternation h ~ p/t/k via the new `stem` field (raanuh:raanup-), (b) the full AHCI/AHCIN allomorph sets incl. =ahte, (c) in=/inci=/e-i-/an-e-/eci-…-yan person-marking strings so inflected tokens (inranu, ikoiraanuh, eciasis…) resolve to lemmas.
7. **Orthography migrations** in the §4 priority order; the vowel-length audit (~147 doublet groups) is the highest-value single pass and the raanu/rannu case is its template.

Files for review:
- `/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/input/sakhalin/sakaguchi_candidates.json`
- `/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/input/sakhalin/sakaguchi_paradigm.json`
- `/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/input/sakhalin/sakaguchi_orthography_proposal.md`