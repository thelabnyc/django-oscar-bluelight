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


def get_sql_range_product_triggers():
    sql_range_product_triggers = [
        """
        CREATE OR REPLACE FUNCTION refresh_offer_rangeproductset()
            RETURNS trigger AS
            $BODY$
            BEGIN
                if not COALESCE(current_setting('oscarbluelight.disable_triggers', true)::boolean, false) then
                    REFRESH MATERIALIZED VIEW CONCURRENTLY offer_rangeproductset;
                end if;
                RETURN NULL;
            END;
            $BODY$
            LANGUAGE PLPGSQL;
        """,
    ]
    range_product_trigger_tables = [
        "catalogue_category",
        "catalogue_product",
        "catalogue_productcategory",
        "catalogue_productclass",
        "offer_range",
        "offer_range_classes",
        "offer_range_excluded_products",
        "offer_range_included_categories",
        "offer_rangeproduct",
    ]
    for table_name in range_product_trigger_tables:
        for event in "INSERT", "UPDATE", "DELETE":
            sql_range_product_triggers.append(
                """
                DROP TRIGGER IF EXISTS refresh_refresh_offer_rangeproductset_{event} ON {table} CASCADE;
            """.format(
                    event=event, table=table_name
                )
            )
            sql_range_product_triggers.append(
                """
                CREATE TRIGGER refresh_refresh_offer_rangeproductset_{event}
                AFTER {event} ON {table}
                FOR EACH STATEMENT
                EXECUTE PROCEDURE refresh_offer_rangeproductset();
            """.format(
                    event=event, table=table_name
                )
            )
    return sql_range_product_triggers
