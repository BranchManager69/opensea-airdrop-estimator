WITH wallet AS (
    SELECT CAST({{wallet}} AS VARBINARY) AS addr
),
deduped_trades AS (
    SELECT *
    FROM (
        SELECT
            block_time,
            amount_original,
            amount_usd,
            collection,
            buyer,
            seller,
            platform_fee_amount,
            platform_fee_amount_usd,
            royalty_fee_amount,
            royalty_fee_amount_usd,
            unique_trade_id,
            ROW_NUMBER() OVER (PARTITION BY unique_trade_id ORDER BY block_time DESC) AS rn
        FROM nft.trades
        WHERE project = 'opensea'
          AND evt_type = 'Trade'
          AND amount_original IS NOT NULL
          AND (
                buyer  = (SELECT addr FROM wallet)
             OR seller = (SELECT addr FROM wallet)
          )
    ) t
    WHERE rn = 1
),
fills AS (
    SELECT
        block_time                        AS tx_time,
        amount_original                   AS price_eth,
        amount_usd,
        collection,
        platform_fee_amount,
        platform_fee_amount_usd,
        royalty_fee_amount,
        royalty_fee_amount_usd,
        CASE
            WHEN buyer = wallet.addr THEN 'buyer'
            ELSE 'seller'
        END                               AS side
    FROM deduped_trades
    CROSS JOIN wallet
),
summary AS (
    SELECT
        COUNT(*)                                                             AS trade_count,
        SUM(CASE WHEN side = 'buyer'  THEN 1 ELSE 0 END)                     AS buy_trade_count,
        SUM(CASE WHEN side = 'seller' THEN 1 ELSE 0 END)                     AS sell_trade_count,
        COALESCE(SUM(price_eth), 0)                                          AS total_eth,
        COALESCE(SUM(amount_usd), 0)                                         AS total_usd,
        COALESCE(SUM(CASE WHEN side = 'buyer'  THEN price_eth END), 0)       AS eth_bought,
        COALESCE(SUM(CASE WHEN side = 'seller' THEN price_eth END), 0)       AS eth_sold,
        COALESCE(SUM(platform_fee_amount), 0)                                AS platform_fee_eth,
        COALESCE(SUM(platform_fee_amount_usd), 0)                            AS platform_fee_usd,
        COALESCE(SUM(royalty_fee_amount), 0)                                 AS royalty_fee_eth,
        COALESCE(SUM(royalty_fee_amount_usd), 0)                             AS royalty_fee_usd,
        MIN(tx_time)                                                         AS first_trade,
        MAX(tx_time)                                                         AS last_trade
    FROM fills
),
buyer_seller AS (
    SELECT
        side,
        COUNT(*)                             AS trade_count,
        COALESCE(SUM(price_eth), 0)          AS total_eth,
        COALESCE(SUM(amount_usd), 0)         AS total_usd,
        COALESCE(SUM(platform_fee_amount), 0) AS platform_fee_eth,
        COALESCE(SUM(royalty_fee_amount), 0)  AS royalty_fee_eth
    FROM fills
    GROUP BY side
),
collection_ranked AS (
    SELECT
        collection,
        COUNT(*)                     AS trade_count,
        COALESCE(SUM(price_eth), 0)  AS total_eth,
        COALESCE(SUM(amount_usd), 0) AS total_usd,
        COALESCE(SUM(platform_fee_amount), 0) AS platform_fee_eth,
        COALESCE(SUM(royalty_fee_amount), 0)  AS royalty_fee_eth,
        ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(amount_usd), 0) DESC) AS rn
    FROM fills
    GROUP BY collection
)

SELECT
    'summary' AS section,
    'overall' AS label,
    trade_count,
    total_eth,
    total_usd,
    platform_fee_eth,
    royalty_fee_eth,
    first_trade,
    last_trade,
    CAST(NULL AS BIGINT)          AS rank,
    buy_trade_count,
    sell_trade_count,
    eth_bought,
    eth_sold,
    platform_fee_usd,
    royalty_fee_usd
FROM summary

UNION ALL

SELECT
    'buyer_seller' AS section,
    side           AS label,
    trade_count,
    total_eth,
    total_usd,
    platform_fee_eth,
    royalty_fee_eth,
    CAST(NULL AS TIMESTAMP) AS first_trade,
    CAST(NULL AS TIMESTAMP) AS last_trade,
    CAST(NULL AS BIGINT)    AS rank,
    CAST(NULL AS BIGINT)    AS buy_trade_count,
    CAST(NULL AS BIGINT)    AS sell_trade_count,
    CAST(NULL AS DOUBLE)    AS eth_bought,
    CAST(NULL AS DOUBLE)    AS eth_sold,
    CAST(NULL AS DOUBLE)    AS platform_fee_usd,
    CAST(NULL AS DOUBLE)    AS royalty_fee_usd
FROM buyer_seller

UNION ALL

SELECT
    'collection' AS section,
    collection   AS label,
    trade_count,
    total_eth,
    total_usd,
    platform_fee_eth,
    royalty_fee_eth,
    CAST(NULL AS TIMESTAMP) AS first_trade,
    CAST(NULL AS TIMESTAMP) AS last_trade,
    rn                      AS rank,
    CAST(NULL AS BIGINT)    AS buy_trade_count,
    CAST(NULL AS BIGINT)    AS sell_trade_count,
    CAST(NULL AS DOUBLE)    AS eth_bought,
    CAST(NULL AS DOUBLE)    AS eth_sold,
    CAST(NULL AS DOUBLE)    AS platform_fee_usd,
    CAST(NULL AS DOUBLE)    AS royalty_fee_usd
FROM collection_ranked
WHERE rn <= 25;
