# Publication and citation

## How to cite

Source edition **0.8.0**, dated November 9, 2026. Cite inspected source by
repository, version, and exact revision. Source, release, standalone manuscript,
and compiled volume remain distinct objects; each needs separate evidence:

> Friedman, D. A. (2026). *The Line Set: The Collected Volume* (source
> version 0.8.0) [Software source]. <https://github.com/docxology/line_set>.

```bibtex
@software{friedman_line_set_source_2026,
  author  = {Friedman, Daniel Ari},
  title   = {The Line Set: The Collected Volume},
  version = {0.8.0},
  year    = {2026},
  url     = {https://github.com/docxology/line_set},
  note    = {Software-source edition; not a manuscript or compiled-volume deposit receipt}
}
```

The owner-chosen **Collected Volume** display title is retained. It labels
this software-source citation, not evidence of a public compiled-volume
deposit. Three objects remain separate:

- The public Main software SOURCE ZIP; previously verified **0.7.0** /
  <https://doi.org/10.5281/zenodo.24069475>.
- The standalone wrapper paper, *The Line Set: Holding Instruments Apart*.
  A source-ZIP DOI does not independently identify a rendered PDF/HTML/EPUB.
- The **PRIVATE eleven-work omnibus**, excluding Witness. No omnibus deposit
  or DOI is claimed, and source publication does not authorize its disclosure.

The older archive remains *The Line Set: Holding Instruments Apart*,
**0.2.0** / <https://doi.org/10.5281/zenodo.22833507>; its title/DOI pair is
historical, not renamed to match the intentional current display title.
Both earlier references remain in `CITATION.cff`; the config's
`publication.archived_version` / `publication.archived_version_doi` now name
the previously verified **0.7.0 source ZIP**. Neither older DOI identifies
proposed 0.8.0. Cite later source through its repository until its exact
edition/object is independently verified.

`CITATION.cff` carries the citation metadata in machine-readable form, and
`.zenodo.json` carries the deposit metadata. The version declarations are
synchronized with `docs/manuscript/config.yaml`; publication metadata is checked
by `tests/test_publication_metadata.py`.

On 2026-10-21 the [Zenodo API](https://zenodo.org/api/records/22833507)
reported the historical DOI as version 0.2.0 under the title
*The Line Set: Holding Instruments Apart*. Preserve that observed identity
and the owner's separate Collected Volume display-title decision. Any future
deposit must describe its actual object; title similarity is not evidence that
a source archive, standalone wrapper, and private omnibus are the same object.
The [archived identity receipt](releases/evidence/archived-identity-v0.2.0.json)
binds that reference's title, version and DOI to the retained API response hash.

## Persistent Identifiers and Verification

The metadata retains exact historical source/version references, not identifiers
for this later edition. Placeholder DOI strings are not citations. Local
metadata assertions do not independently verify a deposit: check the actual
external record, its repository, tag, version, access, and deposited contents.
A reserved identifier is not evidence that a deposit has been published.

## Manual reserve-first DOI publication

This is an alternative for a specifically owner-authorized object, not a
prerequisite for the normal authorized public GitHub Release plus existing
Zenodo hook workflow.

1. Create the authorized Zenodo draft without publishing and reserve its DOI.
2. Verify the reservation and exact object/version/access metadata externally.
   Record the reservation as reserved, not as a published source identity.
   Do not replace a source archive's identifier with a standalone paper's DOI
   or move an older DOI into current citation/config fields.
3. Prepare and re-render that object's DOI-bearing artifacts, inspect them, and
   retain checksums and provenance appropriate to the authorized access scope.
4. Upload and publish only the authorized object, then independently verify its
   actual record and deposited contents. A local test or metadata edit is not
   a publication receipt. A published exact-edition DOI may occupy supported
   current citation/config fields; permanent DOI absence is not the policy.

## The other works

This work is one of the collected set. The works reference each other by name,
repository URL, and — where minted — DOI. Native instruments do not import
siblings; Main reads their published bindings, and Witness accepts reports by
value. The shared envelope schema is aligned by published convention rather
than a runtime dependency between instruments. The membership is declared in
`src/line_set/registry.py`; this table is a citation convenience and does not
define it.

The DOI column below preserves the historical bibliographic cohort; it is not
a current-release inventory.

| Work | Role | Repository | DOI |
| --- | --- | --- | --- |
| `red_line` | line — what I refuse (personal security boundary) | <https://github.com/docxology/red_line> | `https://doi.org/10.5281/zenodo.21754240` |
| `black_line` | line — how I try to do strong work (declaration coverage) | <https://github.com/docxology/black_line> | `https://doi.org/10.5281/zenodo.21754236` |
| `golden_line` | line — what is worth reaching toward (directional readings) | <https://github.com/docxology/golden_line> | `https://doi.org/10.5281/zenodo.21754238` |
| `white_line` | line — what is absent, withheld, or unknowable (absence ledger) | <https://github.com/docxology/white_line> | `https://doi.org/10.5281/zenodo.21754242` |
| `witness_register` | companion beside the set — co-registration without aggregation | <https://github.com/docxology/witness_register> | `https://doi.org/10.5281/zenodo.21754246` |
| `silver_line` | memory and succession | <https://github.com/docxology/silver_line> | Not asserted here |
| `violet_line` | PRIVATE consent records; authorized access only | <https://github.com/docxology/violet_line> | Not asserted here |
| `blue_line` | continuing stewardship | <https://github.com/docxology/blue_line> | Not asserted here |
| `green_line` | capacity under development | <https://github.com/docxology/green_line> | Not asserted here |
| `copper_line` | PRIVATE finite-resource arithmetic and burden attribution | <https://github.com/docxology/copper_line> | No DOI claimed |
| `iron_line` | PRIVATE scenario-bound recorded recovery comparisons | <https://github.com/docxology/iron_line> | No DOI claimed |

The current declaration has ten instruments. Main is their colorless reader;
Witness is separate. Repository names for private works are access-aware
references, not public source or provenance disclosure. The complete eleven-work
omnibus is PRIVATE. Preserve earlier bibliographic cohort identities above.

The owner authorized the November 8, 2026 campaign's GitHub Releases with the
existing public Zenodo hooks active. That dated authority is not evidence of
this candidate's publication or blanket future authority. For a future
owner-authorized release, inspect authenticated hooks immediately before
publication, retain the authorized existing public integration, and verify
each resulting record's repository, tag, version, access, and contents.
Never guess a DOI, assign an older object's DOI to later source, or amend
immutable tags to insert a later identifier. PyPI, private-source disclosure,
and new private deposit automation remain unauthorized.

## Before a public release

- [ ] Every gate in `AGENTS.md` green on a clean checkout.
- [ ] `LICENSE` present and accurate.
- [ ] No absolute local paths, secrets, or PRIVATE producer provenance in tracked
      source or assets. Review Violet, Copper, and Iron separately; allowed public
      package names do not authorize their commits, paths, receipts, or contents.
- [ ] Git history and staged files reviewed for unauthorized private content;
      preserve existing history and immutable tags rather than rewriting them.
- [ ] The rendered PDF regenerated at the release tree.
