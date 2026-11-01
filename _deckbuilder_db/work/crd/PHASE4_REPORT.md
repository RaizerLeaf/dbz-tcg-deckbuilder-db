# Phase 4 report: MP index and Mastery index

Regenerate: `python scripts/mps.py` (after `crd.py`).

## mps.json
- 666 Main Personality printings -> 62 groups (MP name + alignment). Vegeta, Android 18 and Buu appear as both Hero and Villain groups;
  each is separate because a set must share name and alignment.
- Every group has at least one printing of each Level 1-4 (no group is missing a level).
- Per printing: set, card number, rarity, subtitle, PUR, 11 power stages, current power text, printed Traits, effective Traits, errata/MRP flags.
- Per group: `trait_availability` (for each Trait, the printings per level and whether all four levels have it), `fanz_saiyan_mastery_possible`,
  `fanz_namekian_mastery_possible`, `panz_heritage` (Rulebook 3.0 list), `fused_from` and `cannot_include_allies_named`.
- FanZ-eligible for a Saiyan Mastery (Trait on all four levels): 19 groups. For a Namekian Mastery: 8 groups.
  Four groups are Saiyan-eligible under the FanZ Trait rule but not on the Rulebook 3.0 heritage list (they are FanZ-only characters):
  Cabba, Fused Zamasu, Goku Black, Kid Trunks.
- Captain Ginyu (Villain) is not eligible for either Mastery: Saiyan only appears on the "Body Change" level, Namekian only on the Frog/Back in Action levels.
- Future Gohan: no Future Gohan MP card exists in the images, so there is no group. The rule is recorded in `_meta.rules`.
- Fused MPs present: Vegito and Gotenks (Hero), Fused Zamasu (Villain). No Gogeta or Kefla cards exist in the images.

## Traits
- Printed Traits are used as printed. For PanZ-era Main Personality and Ally printings (which print none) the CRD's retroactive Trait list is applied by
  character name (Captain Ginyu "Body Change" gets Saiyan, "Frog" gets Namekian, Goku "Super Saiyan God" gets God), recorded in `traits_source`.
- Cross-check: no printed FanZ Trait set contradicts the CRD's retroactive list (0 mismatches).
- PanZ Allies/MPs whose name is not on the CRD list keep no Traits (`traits_source`: "none printed; not on the CRD retroactive list").

## masteries.json
- 74 Mastery printings -> 42 Mastery names across the six Styles (Black, Blue, Namekian, Orange, Red, Saiyan).
- `cards_restricted_to_this_mastery`: cards whose "(X Mastery only.)" text names the Mastery (e.g. Red Relentless Mastery 4, Saiyan Defiant Mastery 4).
- One card is restricted to a generic "Saiyan Mastery" (S09 BST_61 Vegeta, The Crown Prince); listed under `_meta.style_wide_restrictions`.

## Limits
- Saiyan/Namekian eligibility is computed from the Traits above; it does not check Allies, alignment-only or Named cards for the deck.
- Stage/PUR values are as transcribed in Phase 2 (not yet re-verified; Phase 5).
