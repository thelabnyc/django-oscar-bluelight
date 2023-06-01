from psycopg2 import sql

# Basically copied from the query run by ``oscar.apps.offer.models.Range.product_queryset``
# Just slightly altered to work as a materialized view, leading to better performance.
# At time of writing this, calls to Range.contains_product took about 10ms. With the addition of the
# materialized view the same calls were less than 0.2ms.
SQL_RANGE_PRODUCTS = r"""
SELECT
    RANK() OVER (ORDER BY rng1.id, p1.id) as "id",
    rng1.id as "range_id",
    p1.id as "product_id"
FROM (
    SELECT id FROM offer_range
) rng1
LEFT JOIN LATERAL (
    SELECT DISTINCT catalogue_product.id
    FROM catalogue_product
    LEFT OUTER JOIN catalogue_productcategory ON (catalogue_product.id = catalogue_productcategory.product_id)
    LEFT OUTER JOIN offer_rangeproduct ON (catalogue_product.id = offer_rangeproduct.product_id)
    WHERE (
        (
            (
                catalogue_product.product_class_id IN (
                    SELECT U0.id
                    FROM catalogue_productclass U0
                    INNER JOIN offer_range_classes U1 ON (U0.id = U1.productclass_id)
                    WHERE U1.range_id = rng1.id
                )
                OR
                catalogue_productcategory.category_id IN (
                    SELECT V0.id
                    FROM catalogue_category V0
                    WHERE EXISTS (
                        SELECT U0.id
                        FROM catalogue_category U0
                        INNER JOIN offer_range_included_categories U1 ON (U0.id = U1.category_id)
                        WHERE (
                            U1.range_id = rng1.id
                            AND
                            U0.depth <= (V0.depth)
                            AND
                            (V0.path) LIKE
                                REPLACE(REPLACE(REPLACE(U0.path::text, E'\\\\', E'\\\\\\\\'), E'%', E'\\\\%'), E'_', E'\\\\_') || '%'
                        )
                    ) = TRUE
                )
            )
            OR offer_rangeproduct.range_id = rng1.id
            OR catalogue_product.parent_id IN (
                SELECT W0.id
                FROM catalogue_product W0
                LEFT OUTER JOIN catalogue_productcategory W2 ON (W0.id = W2.product_id)
                LEFT OUTER JOIN offer_rangeproduct W4 ON (W0.id = W4.product_id)
                WHERE (
                    (
                        W0.product_class_id IN (
                            SELECT U0.id
                            FROM catalogue_productclass U0
                            INNER JOIN offer_range_classes U1 ON (U0.id = U1.productclass_id)
                            WHERE U1.range_id = rng1.id
                        )
                        OR
                        W2.category_id IN (
                            SELECT V0.id
                            FROM catalogue_category V0
                            WHERE EXISTS (
                                SELECT U0.id
                                FROM catalogue_category U0
                                INNER JOIN offer_range_included_categories U1 ON (U0.id = U1.category_id)
                                WHERE (
                                    U1.range_id = rng1.id
                                    AND
                                    U0.depth <= (V0.depth)
                                    AND
                                    (V0.path) LIKE
                                        REPLACE(REPLACE(REPLACE(U0.path::text, E'\\\\', E'\\\\\\\\'), E'%', E'\\\\%'), E'_', E'\\\\_') || '%'
                                )
                            ) = TRUE
                        )
                    )
                    OR
                    W4.range_id = rng1.id
                )
            )
        )
        AND NOT (
            (
                (
                    catalogue_product.parent_id IN (
                        SELECT U0.id
                        FROM catalogue_product U0
                        INNER JOIN offer_range_excluded_products U1 ON (U0.id = U1.product_id)
                        WHERE U1.range_id = rng1.id
                    )
                    AND
                    catalogue_product.parent_id IS NOT NULL
                )
                OR
                catalogue_product.id IN (
                    SELECT U0.id
                    FROM catalogue_product U0
                    INNER JOIN offer_range_excluded_products U1 ON (U0.id = U1.product_id)
                    WHERE U1.range_id = rng1.id
                )
            )
        )
    )
) p1 ON true
WHERE p1.id IS NOT NULL
ORDER BY range_id, product_id;
"""


def get_recalculate_offer_application_totals_sql(
    Order,
    OrderDiscount,
    ConditionalOffer,
    ignored_order_statuses,
):
    status_filter = sql.SQL("")
    if len(ignored_order_statuses) > 0:
        status_filter = sql.SQL("AND o.status NOT IN ({statuses})").format(
            statuses=sql.SQL(", ").join(
                [sql.Literal(status) for status in ignored_order_statuses]
            ),
        )
    update_sql = sql.SQL(
        """
        WITH cte_discounts AS (
            -- First query finds all of the discounts, excluding orders ignored
            -- by the status filter
            SELECT d.offer_id as "offer_id",
                   SUM(d.amount) as "calculated_total_discount",
                   SUM(d.frequency) as "calculated_num_applications",
                   COUNT(DISTINCT d.order_id) as "calculated_num_orders"
              FROM {order_orderdiscount} d
              JOIN {order_order} o
                ON o.id = d.order_id
               {status_filter}
             GROUP BY d.offer_id
            UNION
            -- Second query finds all of the offers with no discounts at all
            SELECT co.id as "offer_id",
                   0 as "calculated_total_discount",
                   0 as "calculated_num_applications",
                   0 as "calculated_num_orders"
              FROM {offer_conditionaloffer} co
              LEFT JOIN {order_orderdiscount} d
                ON d.offer_id = co.id
             WHERE d.id IS NULL
             GROUP BY co.id
        ),
        cte_offers_to_update AS (
            SELECT o.id,
                   d.*
              FROM {offer_conditionaloffer} o
              JOIN cte_discounts d
                ON d.offer_id = o.id
             WHERE o.total_discount != d.calculated_total_discount
                OR o.num_applications != d.calculated_num_applications
                OR o.num_orders != d.calculated_num_orders
        )
        UPDATE {offer_conditionaloffer}
           SET total_discount = d.calculated_total_discount,
               num_applications = d.calculated_num_applications,
               num_orders = d.calculated_num_orders
          FROM cte_offers_to_update d
         WHERE d.id = offer_conditionaloffer.id
    """
    ).format(
        order_order=sql.Identifier(Order._meta.db_table),
        order_orderdiscount=sql.Identifier(OrderDiscount._meta.db_table),
        offer_conditionaloffer=sql.Identifier(ConditionalOffer._meta.db_table),
        status_filter=status_filter,
    )
    return update_sql
