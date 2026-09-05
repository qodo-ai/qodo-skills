# Qodo Codex branding

`qodo.png` is the 300×300 Qodo brand icon served by the official
[Qodo website](https://www.qodo.ai/wp-content/uploads/2025/03/qodo-fav-300x300.png)
(checked: 2026-09-05). The CDN returned lossless WebP despite the PNG URL;
it was decoded and re-encoded as PNG without resizing or changing the design.
Source SHA-256: `505d7841292488b3d76c2c3135253a6bdd804d771829cbba1f02c75287041cff`.
Bundled PNG SHA-256: `3b55f9064c1bd1c68de454db1c0056baaf3d881946770a94dc7252f3ce1ebeab`.

The Codex adapter generator copies it into each package as `assets/qodo.png`,
referenced by both `interface.composerIcon` and `interface.logo`.
No network fetch is performed during adapter generation or release packaging.
