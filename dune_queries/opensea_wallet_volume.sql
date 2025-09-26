with fills as (
    select
        block_time   as tx_time,
        taker        as trader,
        price_eth    as eth_amount,
        price_usd    as usd_amount,
        token_set_name as collection,
        case when taker_side = 'buy' then 'buyer' else 'seller' end as side
    from nft.trades
    where platform = 'opensea'
      and lower(taker) = lower({{wallet}})
)
select
    count(*)                            as trade_count,
    coalesce(sum(eth_amount), 0)        as total_eth,
    coalesce(sum(usd_amount), 0)        as total_usd,
    min(tx_time)                        as first_trade,
    max(tx_time)                        as last_trade
from fills;
