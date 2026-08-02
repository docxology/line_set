# Manuscript contract

Markdown sources for the Line Set paper. The manuscript explains what the line set
is, reads the sibling packages, and checks for shared-token collisions.

## Composition order (lexical filename order)

- `00_abstract.md` — abstract
- `01_introduction.md` — introduction: what keeps four instruments from becoming one
- `01b_the_set.md` — the set: four questions, four jobs, and one shared word
- `02_method.md` — method: a declaration, a staged reader, and one seam
- `02a_formalism.md` — the instrument stated formally
- `02b_scholarship.md` — scholarship: what is old about this problem
- `03_extensibility.md` — extensibility: adding a colour is an edit to one file
- `04_examples.md` — worked readings
- `05_limits.md` — limits and epistemic boundaries
- `06_conclusion.md` — conclusion
- `99_references.md` — references heading

## Configuration

- `config.yaml` — title, authors, publication metadata, page geometry
- `preamble.md` — LaTeX preamble directives
- `references.bib` — bibliography

## Reading record

- `reading_record.json` — a dated reading of the installed sibling packages,
  written by `scripts/record_reading.py`; the manuscript bindings test gates
  drift between this record and the prose.
