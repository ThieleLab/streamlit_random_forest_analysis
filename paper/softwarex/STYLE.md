# Style note for the FastForest paper (readability pass)

Readers, in order: a bioinformatician who has never opened the repository; Ines; a SoftwareX reviewer
with thirty minutes. Every sentence should survive all three.

## Sentences and paragraphs
- Say the point first, then the evidence. Each paragraph opens with the sentence a hurried reader could
  stop after.
- One idea per paragraph. If a paragraph has two "but"s, split it.
- Sentences average under 25 words; none over 40. A sentence with three numbers becomes two sentences, or
  the numbers go to the table and the sentence states the comparison ("about a tenth of Boruta's set").
- At most one dash per paragraph. Semicolon lists of at most three items; longer lists become sentences
  or a table.
- Put the meaning before the number: "it kept 27 of the 8,306 reactions" rather than "27 (of 8,306)".
- Verbs over nouns: "the search stops" not "termination of the search occurs".
- British spelling. "we" for what the authors did; "FastForest" or "the tool" for what the software does;
  never "the method" and "the tool" for the same thing in one paragraph.

## Terms
- Define each term once, at first use, and then use only that term: *bound* (the allowed drop of a
  validation metric), *sufficient set* (the smallest set that satisfies the bound), *core* (features
  selected under every seed), *all-relevant set* (Boruta's target), *stage* (S0–S7).
- "Features" everywhere except where the table's columns are reactions, genes or pixels and saying so helps.
- "Test accuracy" is the accuracy on the test split of the final model; say "validation" only for
  decisions. Never "performance" on its own.

## Numbers
- Every number carries its ledger ID in a LaTeX comment. No number enters the text without a ledger row.
- Means with their SD where the SD is in the table; in the text, a mean alone is acceptable when the SD
  is in the table it refers to.
- Percent with one decimal for accuracy, none for reduction; counts with thousands separators.
- Ranges give their ends and name the tables that set them ("2–11 times, from 2.0 at genus level to
  11.0 at order level").

## What not to change
- The SoftwareX structure and section titles.
- The figures, the tables' numbers, the reference list, the code-metadata table.
- The red author notes: each stays until its question is answered.

## Words to avoid
honest, simply, clearly, obviously, robust (unless defined), leverage, novel, powerful, state-of-the-art,
"it is worth noting", "in order to", "the fact that".
