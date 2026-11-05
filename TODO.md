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
