from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from psycopg2.sql import Composed

    from .models import Voucher

try:
    try:
        from psycopg import sql
    except ImportError:
        from psycopg2 import sql
except ImportError:
    raise ImproperlyConfigured("Error loading psycopg2 or psycopg module")


def get_update_children_meta_sql(Voucher: type[Voucher]) -> Composed:
    query = sql.SQL(
        """
        UPDATE {voucher_table} AS cv
           SET name = null,
               usage = pv.usage,
               start_datetime = pv.start_datetime,
               end_datetime = pv.end_datetime,
               limit_usage_by_group = pv.limit_usage_by_group,
               status = pv.status
          FROM {voucher_table} pv
         WHERE cv.parent_id = pv.id
           AND pv.id = {parent_id}
           AND (
                cv.name != null OR
                cv.usage != pv.usage OR
                cv.start_datetime != pv.start_datetime OR
                cv.end_datetime != pv.end_datetime OR
                cv.limit_usage_by_group != pv.limit_usage_by_group OR
                cv.status != pv.status
           );
        """
    ).format(
        voucher_table=sql.Identifier(Voucher._meta.db_table),
        parent_id=sql.Placeholder("parent_id"),
    )
    return query


def _get_insupd_m2m_sql(
    Voucher: type[Voucher], m2m_table_name: str, rel_column_name: str
) -> Composed:
    query = sql.SQL(
        """
        INSERT INTO {m2m_table_name} (voucher_id, {rel_column_name})
        SELECT cv.id,
               pvmm.{rel_column_name}
          FROM {voucher_table} cv
          JOIN {voucher_table} pv
            ON pv.id = cv.parent_id
           AND pv.id = {parent_id}
          JOIN {m2m_table_name} pvmm
            ON pvmm.voucher_id = pv.id
         WHERE NOT EXISTS (
                SELECT 1
                  FROM {m2m_table_name} cvmm
                 WHERE cvmm.voucher_id = cv.id
                   AND cvmm.{rel_column_name} = pvmm.{rel_column_name}
               );
        """
    ).format(
        voucher_table=sql.Identifier(Voucher._meta.db_table),
        m2m_table_name=sql.Identifier(m2m_table_name),
        rel_column_name=sql.Identifier(rel_column_name),
        parent_id=sql.Placeholder("parent_id"),
    )
    return query


def _get_prune_m2m_sql(
    Voucher: type[Voucher], m2m_table_name: str, rel_column_name: str
) -> Composed:
    query = sql.SQL(
        """
        DELETE FROM {m2m_table_name}
         WHERE voucher_id IN (
            SELECT id
              FROM {voucher_table}
             WHERE parent_id = {parent_id}
            )
           AND {rel_column_name} NOT IN (
            SELECT {rel_column_name}
              FROM {m2m_table_name}
             WHERE voucher_id = {parent_id}
            )
        """
    ).format(
        voucher_table=sql.Identifier(Voucher._meta.db_table),
        m2m_table_name=sql.Identifier(m2m_table_name),
        rel_column_name=sql.Identifier(rel_column_name),
        parent_id=sql.Placeholder("parent_id"),
    )
    return query


def get_insupd_children_offers_sql(Voucher: type[Voucher]) -> Composed:
    query = _get_insupd_m2m_sql(
        Voucher,
        "%s_offers" % Voucher._meta.db_table,
        "conditionaloffer_id",
    )
    return query


def get_prune_children_offers_sql(Voucher: type[Voucher]) -> Composed:
    query = _get_prune_m2m_sql(
        Voucher,
        "%s_offers" % Voucher._meta.db_table,
        "conditionaloffer_id",
    )
    return query


def get_insupd_children_groups_sql(Voucher: type[Voucher]) -> Composed:
    query = _get_insupd_m2m_sql(
        Voucher,
        "%s_groups" % Voucher._meta.db_table,
        "group_id",
    )
    return query


def get_prune_children_groups_sql(Voucher: type[Voucher]) -> Composed:
    query = _get_prune_m2m_sql(
        Voucher,
        "%s_groups" % Voucher._meta.db_table,
        "group_id",
    )
    return query
