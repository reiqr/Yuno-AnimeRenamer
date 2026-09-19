# UI Preview 12 — UI asset sizing manifest

Preview 12 introduced pre-scaled UI artwork so images stay crisp and proportionate at compact and wider window sizes.

Source patch archive:
- `AnimeRenamer_FutureDiary_UI_preview12_patch.zip`
- SHA256: `6e7c3fd824d8be5645609a74f485984cb84a14fe8c06e5487f3616eaf47bccd1`

Files:

| File | Size | SHA256 |
| --- | ---: | --- |
| `AnimeRenamer.pyw` | 71,529 B | `095c998081cefe6a7923f6ae3a5f36fc1dfb3afbd83ef0e238f40701ac45018f` |
| `assets/empty_phone.png` | 8,977 B | `be312330056f5d3183e496160592ee529cfc201d92fb2fff5926c5fc401ea91d` |
| `assets/yuno_banner.png` | 94,485 B | `7873ba1996264f9221d6e1f11c2829324dc069ed48e3f5e44045ff8fe32943ca` |
| `assets/yuno_banner_wide.png` | 115,196 B | `0c70ad937ee17c1600278124cf89654ba6609a6048de474481fae7d47b6d8e5c` |
| `assets/yuno_sidebar.png` | 131,160 B | `eabf01bf346aa224eccd3eed45d905b27a3381a61ec379d0a56e65be340cec15` |

Design intent:
- sidebar art pre-scaled to the exact compact slot;
- separate compact/wide banner variants;
- a small empty-state phone illustration that supports the UI without taking over the preview area.
