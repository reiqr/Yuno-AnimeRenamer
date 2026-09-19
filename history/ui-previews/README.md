# AnimeRenamer UI preview history — 2026-09-19

This branch preserves the iterative Mirai Nikki / Yuno themed UI work without polluting `main` with every experimental snapshot.

Base for this archive:
- branch point: `420c9066e0a1cacfddd71984a7104de85b11fdd7`
- branch: `ui-preview-history-20260919`

Earlier work (Preview 1–3 / theme baseline) is already represented by normal repository commits on `main`, including:
- `4b1411c` — apply Mirai Nikki dark theme UI
- `39b767b` — add theme art assets
- `15f5fe1` — themed group dialog and compact layout
- `a735234` — optimize theme art assets
- `c1e1bbe` — bundle theme assets into packaged builds
- `420c906` — stop tracking generated PyInstaller spec

## Archived previews

| Preview | Record | Main focus |
| --- | --- | --- |
| 04 | `preview-04.patch` | dark Windows chrome, themed controls, status strip |
| 05 | `preview-05.patch` | custom themed modal dialogs and stronger preview states |
| 06 | `preview-06.patch` | compact banner, themed focus/scrollbars, empty-state UI |
| 07 | `preview-07.patch` | pill toggles, adaptive preview columns, row hover |
| 08 | `preview-08.patch` | state-color system, group expand markers, pressed states |
| 09 | `preview-09.patch` | code-generated pixel icons and reduced text-button feel |
| 10 | `preview-10.part01.patch` + `preview-10.part02.patch` | card boundaries, progressive field disclosure, more preview height |
| 11 | `preview-11.patch` | unified control sizing, stripe rows, softened/chamfered cards |
| 12 | `preview-12.patch` + `preview-12-assets.md` | image sizing, wide banner variant, small phone empty-state art |
| 13 | `preview-13-assets.md` | banner-only composition revision, removing awkward half-face crop |
| 14 | `preview-14.part01.patch` + `preview-14.part02.patch` + `preview-14.part03.patch` | near-1.0 UI finish: action hierarchy, scan animation, preview-first layout |
| 15 | `preview-15-icon-build.md` | Windows `.ico`, Explorer/EXE icon and build packaging |
| 16 | `preview-16.patch` | rebalance sidebar: lower artwork, distribute text into intro/flow/bottom zones |

## Source patch archive hashes

- Preview 04 ZIP: `f154ef46d6874ff0fa933fc03b10ebf1b052e5870a4b2b330819b7c9aea5ebec`
- Preview 05 ZIP: `0e800f8355457476443b0e75fbbed1883f2258c4b49bf95b0d03a0d5b0b36f87`
- Preview 06 ZIP: `07039124fba2b2eace0d5e241aba4a590688fd95670909cbdbeb1fb229b6031b`
- Preview 07 ZIP: `ba7e81ec0d81122be9f1fabebb47e1d72243a81a5f3437df36934aeabb353ec9`
- Preview 08 ZIP: `d1970eea6e8d74a2a2d29e43ae0ff2d38dc982dba214d0614d757fa86526ae28`
- Preview 09 ZIP: `d8eead101334227bb665ece6d2c6def5ee7353bba24cf9d874cb1a057a2cd582`
- Preview 10 ZIP: `2e303462655abc9a6f8bbc6a9c7aa5f0741cfea5a4ef763cb9c5c8f37a5d4284`
- Preview 11 ZIP: `a2f3bc825f7d1db2e919416b1dc142c2759f710d4279699b53655ea7bf3e7704`
- Preview 12 ZIP: `6e7c3fd824d8be5645609a74f485984cb84a14fe8c06e5487f3616eaf47bccd1`
- Preview 13 ZIP: `afde1b03988c687f0ffae3986feee385ef91411fa356c35ff2b8b1d35fa34e17`
- Preview 14 ZIP: `e1ae1a4df4fd180163a3fa92ae6687edc343f475c74603558d8770767b3caddc`
- Preview 15 ZIP: `e68c56a44d37a5259e3fca818dd05697f053ae06a5704bf6dd3fd4234b8597a0`

## Notes

- These are history/audit records. The archive branch is not intended to be used as the release branch.
- Binary UI assets are represented by SHA256 manifests where direct binary archival through the connector was not appropriate.
- Core rename/copy/undo behavior was intentionally kept unchanged throughout these UI previews.
- Preview 16 continues from the latest Preview 14 UI + Preview 13 banner assets + Preview 15 icon/build configuration and only changes sidebar layout code.
