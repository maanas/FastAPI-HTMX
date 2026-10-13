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
| Alpine.js (CSP build) | 3.17.4 | `app/static/vendor/alpinejs/alpine-csp.min.js` | https://registry.npmjs.org/@alpinejs/csp/-/csp-3.17.4.tgz (`dist/cdn.min.js`; package `@alpinejs/csp`) | MIT | `0d18d7f8d7910e2e0212f0f056b12f50bebc3abb7d88d2f7c7cb4c336fe4519a` | Tarball sha512 verified against `dist.integrity`. Evaluates attributes with its own parser, no `eval` or `new Function`, so a policy needs no `unsafe-eval` |
| htmx | 2.0.11 | `app/static/vendor/htmx/htmx.min.js` | https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.11.tgz (`dist/htmx.min.js`; newest 2.x, `latest`; dist-tag `next` is 4.0.0) | 0BSD | `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717` | Tarball sha512 verified against `dist.integrity` |
| mini-svg-data-uri | 1.4.4 | `theme/node_modules/mini-svg-data-uri/` (`index.js`, `shorter-css-color-names.js`, `package.json`, `LICENSE`) | https://registry.npmjs.org/mini-svg-data-uri/-/mini-svg-data-uri-1.4.4.tgz | MIT | `index.js` `ba166e003f5c552d09e9f417114624653194e36bd7f667042f1b6f47fe9023d8` | Build-time dependency of Flowbite's Tailwind plugin (`theme/flowbite/plugin.js` requires it); not loaded by any page. Tarball sha512 verified against `dist.integrity` |
| Tailwind CLI | 4.3.3 | `build/tailwind/` (standalone binary) | https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-macos-arm64 (other platforms: see `tools/css.sh`) | MIT | macos-arm64 `cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d` | Build tool, downloaded by `tools/css.sh` and checked against the pinned sha256, not committed (80 MB). Its output is `app/static/css/app.css` |
| Inter (variable) | 5.3.0 | `app/static/vendor/inter/` (`inter-latin-wght-normal.woff2`, `inter-latin-ext-wght-normal.woff2`, `LICENSE`) | https://registry.npmjs.org/@fontsource-variable/inter/-/inter-5.3.0.tgz (`files/`, `LICENSE`; package `@fontsource-variable/inter`) | OFL-1.1 | latin `3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62`, latin-ext `34b9c504cab7a73e37b746343a449132e56cf7b5481af2cb81dc74dcff25c956`, `LICENSE` `3b0a5fca3d17942cde889069889dedbbbd075e9b599968c82a95f4d944e9b345` | Weight axis 100-900, normal style only. Declared as family 'Inter' in `app/static/css/src/fonts.css`. Tarball sha512 verified against `dist.integrity` |
