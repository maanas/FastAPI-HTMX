# Vendored files

Every script and stylesheet the pages load is a pinned file under `app/static/vendor/`; nothing loads from another origin.

## Updating a file

1. `curl -fsSL https://registry.npmjs.org/<name>/<version>` and read `dist.tarball`, `dist.integrity`, `license`.
2. Download the tarball with curl into a new empty directory.
3. Verify: `openssl dgst -sha512 -binary <file>.tgz | openssl base64 -A` must equal `dist.integrity` (without the `sha512-` prefix). On a mismatch, stop.
4. `tar -xzf` it, copy out only the one file, byte-identical, and never run anything from the tarball.
5. Update the row below (version, sha256 from `shasum -a 256 <file>`) and delete the scratch directory.

## Files

| Library | Version | File | Source | Licence | sha256 | Note |
|---|---|---|---|---|---|---|
| Flowbite JS | 4.0.2 | `app/static/vendor/flowbite/flowbite.min.js` | https://registry.npmjs.org/flowbite/-/flowbite-4.0.2.tgz (`dist/flowbite.min.js`) | MIT | `049183ea619307bb6f0d1c4abd4fad6d37167409b5b790067d3b637dbd2305f0` | |
| Alpine.js | 3.17.4 | `app/static/vendor/alpinejs/alpine.min.js` | https://registry.npmjs.org/alpinejs/-/alpinejs-3.17.4.tgz (`dist/cdn.min.js`) | MIT | `232519394c6c8fdba6f362b1d9da16106db513cdbf899011f00daab4051df31c` | |
| hyperscript | 0.9.11 | `app/static/vendor/hyperscript/hyperscript.min.js` | https://registry.npmjs.org/hyperscript.org/-/hyperscript.org-0.9.11.tgz (`dist/_hyperscript.min.js`, the package `main`, what unpkg serves) | BSD-2-Clause | `9e63e5162f36c11d8621ab025251a7e28eb421266f1cb10e2b4dcbbbb91a7d1e` | TEMPORARY: removed by the "Hyperscript out" item in TODO.md |
| Flowbite CSS | 1.8.1 | `app/static/vendor/flowbite/flowbite-1.8.1.min.css` | https://registry.npmjs.org/flowbite/-/flowbite-1.8.1.tgz (`dist/flowbite.min.css`) | MIT | `3160d1aead8785eabca7e23e810460543c7c94b2659d518f7f04c1b3d066a7d3` | TEMPORARY: markup is still Flowbite 1.x; replaced by the Tailwind v4 build in the "CSS build" item in TODO.md |
| htmx | 2.0.11 | `app/static/vendor/htmx/htmx.min.js` | https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.11.tgz (`dist/htmx.min.js`; newest 2.x, `latest`; dist-tag `next` is 4.0.0) | 0BSD | `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717` | Tarball sha512 verified against `dist.integrity` |
