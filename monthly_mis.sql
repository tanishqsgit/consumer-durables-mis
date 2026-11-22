-- SQLite. The loader normalizes codes and supplies one valid row per record ID.
WITH actual AS (
  SELECT substr(sale_date, 1, 7) AS month, region,
         SUM(sell_in) AS sell_in, SUM(sell_out) AS sell_out
  FROM sales
  GROUP BY 1, 2
),
periods AS (
  SELECT month, region FROM actual
  UNION
  SELECT month, region FROM targets
)
SELECT p.month, p.region,
       COALESCE(a.sell_in, 0) AS sell_in,
       COALESCE(a.sell_out, 0) AS sell_out,
       t.target_units,
       ROUND(100.0 * COALESCE(a.sell_out, 0) / NULLIF(t.target_units, 0), 1)
         AS attainment_pct,
       ROUND(100.0 * (COALESCE(a.sell_out, 0) - py.sell_out) / NULLIF(py.sell_out, 0), 1)
         AS yoy_pct,
       COALESCE(a.sell_in, 0) - COALESCE(a.sell_out, 0) AS channel_gap_units
FROM periods p
LEFT JOIN actual a USING (month, region)
LEFT JOIN targets t USING (month, region)
LEFT JOIN actual py ON py.region = p.region
  AND py.month = strftime('%Y-%m', date(p.month || '-01', '-1 year'))
ORDER BY p.month, p.region;
