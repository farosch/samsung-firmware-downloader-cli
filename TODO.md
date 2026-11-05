# Open investigation leads

- Coverage: in a sample of 85 models from soundbar, TV and phone keywords, only
  soundbars (`HW-*`) had `FM` firmware entries in product detail. Check whether
  Samsung publishes firmware for TVs and phones through another API or only
  through the download center.
- Search limit: a keyword search returns at most 10 models and has no paging
  parameter. Tried: `page`, `pageIndex`, `pageNo`, `pageSize`, `currentPage`,
  `pageNum`, `offset`, `start`, `from`, `size`, `rows`. Branch and subcategory
  selections work around it through the taxonomy labels. Typed keywords do not.
  If Samsung adds paging, switch the typed-keyword path to it.
- Label searches are fuzzy. A label with no exact match returns unrelated products
  (for example phones under Dishwashers). Decide whether to keep models whose code
  starts with the label, or to keep all results.
- Branch scans are slow: about 45 seconds for Dishwashers (78 models), because each
  label and each model is a request. Consider caching the label lists.
- Discovered firmware has no pinned SHA256, only `Content-Length`. Decide whether
  verified manifests should be generated from discovered entries.
- The download-center listing pages return 403 to scripted clients, so only the
  `downloadUrl` values in product detail are used.
- Many listed models have no product detail page (HTTP 404). They are skipped as
  having no firmware, without a count. Investigate whether the label search is
  returning non-firmware products and report skipped models.
- allow to download a json list of downloads for all or a selection of branches/devices
- Release follow-ups: add an Intel macOS (`x86_64`) binary, which needs a runner that
  still supports it, or a universal2 build. Consider code signing and notarization for
  macOS and Windows, which removes the first-run warnings. The first release has not
  been verified end to end yet.
- 