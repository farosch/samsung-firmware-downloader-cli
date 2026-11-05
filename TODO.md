# Open investigation leads

- Coverage: in a sample of 85 models from soundbar, TV and phone keywords, only
  soundbars (`HW-*`) had `FM` firmware entries in product detail. Check whether
  Samsung publishes firmware for TVs and phones through another API or only
  through the download center.
- Search pagination: `models.json` returned exactly 10 records for every keyword
  tried. Find out whether it accepts a page or offset parameter.
- Branch selection searches by subcategory name, because category leaves carry no
  model codes. A subcategory with many models may return only the first results.
- Discovered firmware has no pinned SHA256, only `Content-Length`. Decide whether
  verified manifests should be generated from discovered entries.
- The download-center listing pages return 403 to scripted clients, so only the
  `downloadUrl` values in product detail are used.
