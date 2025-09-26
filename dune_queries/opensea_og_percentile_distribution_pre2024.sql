WITH filtered_trades AS (
    SELECT *
    FROM (
        SELECT
            block_time,
            amount_original,
            amount_usd,
            buyer,
            seller,
            platform_fee_amount,
            royalty_fee_amount,
            unique_trade_id,
            ROW_NUMBER() OVER (PARTITION BY unique_trade_id ORDER BY block_time DESC) AS rn
        FROM nft.trades
        WHERE project = 'opensea'
          AND evt_type = 'Trade'
          AND amount_original IS NOT NULL
          AND amount_usd BETWEEN 1 AND 10000000
          AND amount_original BETWEEN 0 AND 10000
          AND (COALESCE(platform_fee_amount, 0) > 0 OR COALESCE(royalty_fee_amount, 0) > 0)
          AND block_time <= TIMESTAMP '2023-12-31 23:59:59 UTC'
    ) t
    WHERE rn = 1
),
wallet_events AS (
    SELECT
        buyer   AS wallet,
        block_time,
        amount_original,
        amount_usd,
        platform_fee_amount,
        royalty_fee_amount
    FROM filtered_trades
    WHERE buyer IS NOT NULL

    UNION ALL

    SELECT
        seller  AS wallet,
        block_time,
        amount_original,
        amount_usd,
        platform_fee_amount,
        royalty_fee_amount
    FROM filtered_trades
    WHERE seller IS NOT NULL
),
wallet_aggregates AS (
    SELECT
        wallet,
        MIN(block_time)                                  AS first_trade,
        MAX(block_time)                                  AS last_trade,
        COUNT(*)                                         AS trade_count,
        COALESCE(SUM(amount_original), 0)                AS total_eth,
        COALESCE(SUM(amount_usd), 0)                     AS total_usd,
        COALESCE(SUM(platform_fee_amount), 0)            AS platform_fee_eth,
        COALESCE(SUM(royalty_fee_amount), 0)             AS royalty_fee_eth
    FROM wallet_events
    GROUP BY wallet
),
ranked AS (
    SELECT
        wallet,
        total_usd,
        total_eth,
        platform_fee_eth,
        trade_count,
        NTILE(100) OVER (ORDER BY total_usd DESC)        AS usd_percentile_rank,
        NTILE(100) OVER (ORDER BY total_eth DESC)        AS eth_percentile_rank,
        NTILE(100) OVER (ORDER BY platform_fee_eth DESC) AS fee_percentile_rank
    FROM wallet_aggregates
),
percentile_band AS (
    SELECT
        usd_percentile_rank,
        COUNT(*)                                 AS wallet_count,
        SUM(total_usd)                           AS sum_total_usd,
        SUM(total_eth)                           AS sum_total_eth,
        approx_percentile(total_usd, 0.05)       AS pct05_total_usd,
        approx_percentile(total_usd, 0.95)       AS pct95_total_usd,
        approx_percentile(total_eth, 0.05)       AS pct05_total_eth,
        approx_percentile(total_eth, 0.95)       AS pct95_total_eth
    FROM ranked
    GROUP BY usd_percentile_rank
)

SELECT
    usd_percentile_rank,
    wallet_count,
    pct05_total_usd     AS min_total_usd,
    pct95_total_usd     AS max_total_usd,
    pct05_total_eth     AS min_total_eth,
    pct95_total_eth     AS max_total_eth,
    sum_total_usd,
    sum_total_eth
FROM percentile_band
ORDER BY usd_percentile_rank;
