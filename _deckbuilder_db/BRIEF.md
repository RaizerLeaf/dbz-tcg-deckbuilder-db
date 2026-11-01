# Project brief (from the owner, verbatim)

> Note added for the repository: the brief below was written for the local Windows folder
> `C:\Users\riazm\Downloads\Master PanZ & FanZ Sets`. In this repository that folder is the
> repo root. The CRD and rules PDFs are all in `_rules/` (there is no `zzz_FanZ CRD` folder).

You're helping me build a searchable database of every card in the Dragon Ball Z TCG (Panini "PanZ", Sets 1-7, and the fan-run continuation "FanZ", Sets 8+). The database will be uploaded to another Claude chat that acts as my deck-building assistant, so accuracy matters more than speed. Never guess a card's text. If you can't read it confidently, flag it.

## The folder
The working directory is: C:\Users\riazm\Downloads\Master PanZ & FanZ Sets
Do NOT modify, rename, or move any original card image. Write all output to a new subfolder called _deckbuilder_db.

Contents:
- 01_Set 1 (Premiere) ... 19_Set 19 (Judgement): one folder per set. PanZ = Sets 1-7. FanZ = Set 8 (Celestial Tournament) onward. Each set folder has subfolders such as "(Booster)", "(Starter)", "(Promos)", and possibly others. Inspect the actual structure rather than assuming.
- z_OP Series (OP1-OP6): organized play promos.
- zz_PanZ MP & Ally Promos (subfolders MPs and Allies): PanZ-era promo MPs/Allies, mostly updated versions of PanZ cards that carry newer FanZ additions such as Traits.
- zzz_FanZ CRD: the FanZ Combined Current Rulings Document PDF (v1.15). I'll also put the PanZ Final CRD and Rulebook 3.0 PDFs in a _rules subfolder (ask me if they aren't there).
- All cards are images (JPG/PNG), named like "S05_Goku - Protector of Earth.jpg", "113_Overpowering Attack (Errata).png", "S08_Goku - Super Saiyan (CRD).png". The prefix is the card number (plain number = booster, S = starter, P = promo). Suffixes like (CRD), (Errata), (Frozen) are my own annotations. Record them as flags, and don't assume what they mean beyond that.

## Card anatomy (verified on samples)
Main Personality (MP) card: Level number (1-4) top-left, character NAME and SUBTITLE (e.g. "GOKU / PROTECTOR OF EARTH"), set symbol, card number, 11 Power Stage values down the right side (e.g. 9,001 ... 0), alignment on the right edge (HERO = blue, VILLAIN = red), Power Up Rating (PUR) bottom-left, and the Power text in the bottom box (with icons). From Set 8 on, MPs and Allies also show Trait icons.
Other cards: Mastery (defines the Style), Physical Combat, Energy Combat, Event, Setup, Drill, Ally, Dragon Ball. The card type is printed on the card.
Icons matter: sword = attack, shield = defense, infinity = continuous effect, lightning bolt = instant power. FanZ Set 14+ uses text shorthand such as "2: Energy Attack", plus keywords Focused, Remain X, Unstoppable, Unpreventable, Unmodifiable, Foresee X, and a Desperation icon.
Style = the first word of the card title (Black, Blue, Namekian, Orange, Red, Saiyan). Anything else is Freestyle. "Named" cards have a character name in the title. Watch for parentheticals such as "(Limit 1 per deck.)", "(Hero/Villain only)", "([Trait] only.)", "(Orange Adept Mastery only.)" and "(Banish after use.)".

## Method (do these in order, and STOP for my review after Phase 1)
Phase 0 - Recon: Count the image files per folder, check what's installed (Python, Tesseract, Pillow, OpenCV, etc.) and tell me what you'd like to install. Ask before installing anything. Report the total card count.

Phase 1 - Pilot: Process Set 1 (all subfolders), Set 14, and the zz_PanZ MP & Ally Promos folder only. Use OCR on cropped regions (title bar, text box, stage list) as the cheap first pass, and use your own vision (read the image directly) for every MP, Mastery, and Ally, and for any card where OCR is low-confidence, missing icons/card type, or disagrees with the filename. Show me 10 sample records, your accuracy estimate, and a list of problem cards. Wait for my OK before the full run.

Phase 2 - Full run: Process every folder. Requirements:
- Resumable: cache one JSON per image in _deckbuilder_db/cache so a crash or restart doesn't redo work.
- Log progress and estimated remaining work. Process in batches by set.
- Never skip an image. Anything unreadable gets needs_review=true with a reason.

Phase 3 - Errata and rulings: Parse the CRD PDFs. For every card with an [ERRATUM] or [RULING], attach it to the matching card record(s): original_text (as printed), current_text (after errata), erratum_note, ruling_note, and whether a given printing is the MRP (most recent printing) version. Also record Frozen List status, Gold Title Reprint status, and "Limit N per deck". Where a printing's image already shows the updated text, say so. If a CRD entry can't be matched to a card, list it in the QA report.

Phase 4 - MP grouping: MPs with the same name can mix and match levels across sets (e.g. Set 1 Lv1 Goku + Set 4 Lv2 Goku + Set 7 Lv3 and Lv4 Goku). Build an MP index: for each MP name + alignment, list every available printing of each level 1-4 with set, card number, subtitle, PUR, power stages, power text, and Traits. Treat "Future Gohan" as a separate MP that cannot mix with other Gohans. Fused MPs (Gogeta, Vegito, Gotenks, Kefla, Fused Zamasu) can't run the Allies they're fused from. Note which MP levels have the Saiyan or Namekian Trait, since Saiyan and Namekian Masteries need the Trait on all four chosen levels in FanZ (PanZ used a heritage list).

Phase 5 - Verification: Cross-check card_name against the filename. Check every MP has exactly 11 power stages in descending order and a PUR. Check set counts against the file counts. Re-read a random 5% sample visually and report the error rate. List all needs_review cards.

## Output (in _deckbuilder_db)
- cards.json and cards.csv: one record per printing, with fields: card_id, set_number, set_name, era (PanZ/FanZ), source_folder, collection (booster/starter/promo/OP/etc.), card_number, filename, filename_flags, card_name, subtitle, card_type, style, is_named, named_character, alignment, rarity (if visible), level (MPs), power_stages (list of 11), pur, traits, icons, keywords, limit_per_deck, restrictions (hero/villain only, trait only, mastery only), text_as_printed, text_current (post-errata), errata_note, ruling_note, frozen, gold_title_reprint, is_mrp, ocr_confidence, needs_review, review_reason.
- mps.json: the grouped MP index from Phase 4.
- masteries.json: every Mastery with its Style, text, and set.
- qa_report.md: counts per set, error rates, needs_review list, unmatched CRD entries.
- README.md: the schema and how to regenerate.
Keep each file small enough to upload to a chat (aim for under about 20 MB total; split cards by era if needed).

## Rules
- Be honest about uncertainty. A flagged card is better than a confidently wrong one.
- Ask me before installing software or making any change outside _deckbuilder_db.
- If a card's layout doesn't fit the above, describe it and ask rather than forcing it into a field.
