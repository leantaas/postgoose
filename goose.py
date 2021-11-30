#!/usr/bin/env python

import os
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import PosixPath
from typing import List, Set, Iterable, Optional, T, Tuple
from psycopg2 import connect, OperationalError, IntegrityError, sql

from app_logger import get_app_logger
from goose_version import __version__
from goose_utils import print_args, print_up_down, DBParams, Migration
    

Schema = str

# Defaults
migrations_table = "goose_migrations"

logger = get_app_logger()


def get_migration_id(file_name: str) -> int:
    try:
        return int(file_name.split('_')[0])
    except ValueError:
        raise RuntimeError(
            f'ERROR: File "{file_name}" is not of pattern '
            '"(id)_up.sql" or "(id)_down.sql"')


def get_max_migration_id(filenames: List[str]) -> int:
    return max(get_migration_id(file_name) for file_name in filenames)


def get_migration_files_filtered(dir: PosixPath) -> List[str]:
    return [file for file in os.listdir(dir.as_posix()) if file.lower().endswith(".sql")]


def assert_all_migrations_present(dir: PosixPath) -> None:
    filenames: List[str] = get_migration_files_filtered(dir)
    if not filenames:
        logger.warning(f"Migrations folder {dir} is empty. Exiting gracefully!")
        return

    max_migration_id = get_max_migration_id(filenames)

    for migration_id in range(1, max_migration_id + 1):
        # todo - assertions can be ignored...?
        assert f"{migration_id}_up.sql" in filenames, f"Migration {migration_id} missing ups"
        assert f"{migration_id}_down.sql" in filenames, f"Migration {migration_id} missing downs"

    extra_files: Set[str] = (
        set(filenames)
        - {f"{m_id}_up.sql" for m_id in range(1, max_migration_id + 1)}
        - {f"{m_id}_down.sql" for m_id in range(1, max_migration_id + 1)}
    )

    if extra_files:
        logger.error(f'Extra files not of pattern "<id>_up.sql" or "<id>_down.sql": ')
        print(*extra_files, sep="\n")
        exit(3)


def parse_migrations(dir: PosixPath) -> List[Migration]:
    filenames: List[str] = get_migration_files_filtered(dir)
    max_migration_id: int = get_max_migration_id(filenames)

    migrations: List[Migration] = [
        parse_migration(dir, migration_id) for migration_id in range(1, max_migration_id + 1)
    ]

    return migrations


def parse_migration(dir: PosixPath, migration_id: int) -> Migration:
    up_file: PosixPath = dir.joinpath(f"{migration_id}_up.sql")
    down_file: PosixPath = dir.joinpath(f"{migration_id}_down.sql")

    with open(up_file) as up_fp, open(down_file) as down_fp:

        up = up_fp.read()
        up_digest = digest(up)
        down = down_fp.read()
        down_digest = digest(down)

        migration = Migration(
            migration_id=migration_id,
            up_digest=up_digest,
            up=up,
            down_digest=down_digest,
            down=down,
        )
        return migration


def acquire_mutex(cursor) -> None:
    try:
        cursor.execute(
            f"""
        /* Ideal lock timeout? */
        SET lock_timeout TO '2s';    

        LOCK TABLE {migrations_table} IN EXCLUSIVE MODE;
    """
        )
    except OperationalError as e:
        raise RuntimeError("Migrations already in progress")


def set_search_path(cursor, schema: str) -> None:
    cursor.execute(sql.SQL("set search_path to {}".format(schema)))


def set_role(cursor, role: str) -> None:
    cursor.execute(sql.SQL("set role {}".format(role)))


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("migrations_directory",
        help="Path to directory containing migrations")
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default=5432, type=int)
    parser.add_argument("-P", "--password", default=None)
    parser.add_argument("-U", "--username", default="postgres")
    parser.add_argument("-d", "--database", default="postgres")
    parser.add_argument("-s", "--schema", default="public")
    parser.add_argument("-r", "--role", default=None)
    parser.add_argument(
        "--no_strict_digest_check",
        action="store_false",
        dest='strict_digest_check',
        help="Set False to compare with saved digest "
        "instead of re-computing digest. Default is True",
    )
    parser.add_argument(
        "-m", 
        "--migrations_table_name",
        default=None,
        help="Default is goose_migrations",
    )
    parser.add_argument(
        "--auto_apply_down",
        action="store_true",
        help="Will automatically apply down files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Causes output to be verbose",
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    print_args(args)

    password = args.password or os.getenv("PGPASSWORD")

    if not password:
        raise RuntimeError("PGPASSWORD not set")

    db_params = DBParams(
        user=args.username,
        password=password,
        host=args.host,
        port=args.port,
        database=args.database
    )

    run_migrations(
        args.migrations_directory,
        db_params,
        args.schema,
        args.role,
        args.migrations_table_name,
        args.auto_apply_down,
        args.verbose,
        args.strict_digest_check
    )


def run_migrations(
    migrations_directory,
    db_params,
    schema='public',
    role=None,
    migrations_table_name=None,
    auto_apply_down=False,
    verbose=False,
    strict_digest_check=True
):
    if verbose:
        logger.setLevel('DEBUG')

    migrations_directory = _get_migrations_directory(migrations_directory)

    assert_all_migrations_present(migrations_directory)

    conn = connect(**vars(db_params))

    with conn:
        cursor = conn.cursor()

        set_search_path(cursor, schema)

        if role is not None:
            set_role(cursor, role)

        if migrations_table_name is not None:
            global migrations_table
            migrations_table = migrations_table_name

        CINE_migrations_table(conn.cursor())

        migrations_from_db: List[Migration] = sorted(
            get_db_migrations(conn), key=lambda m: m.migration_id
        )
        migrations_from_filesystem: List[Migration] = sorted(
            parse_migrations(migrations_directory), key=lambda m: m.migration_id
        )

        old_branch, new_branch = get_diff(
            migrations_from_db,
            migrations_from_filesystem,
            strict_digest_check
        )

        acquire_mutex(cursor)

        if old_branch:
            if auto_apply_down:
                unapply_all(cursor, old_branch)
            else:
                logger.error("-a / --auto_apply_down flag is set to false")
                raise RuntimeError(
                    f"failed at migration number: {old_branch[0].migration_id}"
                )
        apply_all(cursor, new_branch)


def apply_all(cursor, migrations) -> None:
    assert (
        sorted(migrations, key=lambda m: m.migration_id) == migrations
    ), "Migrations must be applied in ascending order"
    for migration in migrations:
        apply_up(cursor, migration)


def unapply_all(cursor, migrations) -> None:
    logger.warning(f'Unapplying migrations: {migrations}')
    assert (
        sorted(migrations, key=lambda m: m.migration_id, reverse=True) == migrations
    ), "Migrations must be unapplied in descending order"
    for migration in migrations:
        apply_down(cursor, migration)


def apply_up(cursor, migration: Migration) -> None:

    print_up_down(migration, "up")

    cursor.execute(migration.up)
    cursor.execute(
        f"""
            INSERT INTO {migrations_table} (migration_id, up_digest, up, down_digest, down)
            VALUES (%s, %s, %s, %s, %s);
        """,
        (
            migration.migration_id,
            digest(migration.up),
            migration.up,
            digest(migration.down),
            migration.down,
        ),
    )


def apply_down(cursor, migration: Migration) -> None:
    logger.warning(f'Applying down migration: {migration.down}')
    print_up_down(migration, "down")
    
    # skip empty down migrations
    if migration.down:
        cursor.execute(migration.down)
    cursor.execute(
        f"DELETE FROM {migrations_table}  WHERE migration_id = {migration.migration_id};"
    )


def _get_migrations_directory(pathname: str) -> PosixPath:
    migrations_directory = PosixPath(pathname).absolute()

    if not migrations_directory.is_dir():
        raise RuntimeError(
            f"{migrations_directory.as_posix()} is not a directory"
        )
    else:
        return migrations_directory


def digest(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def get_db_migrations(conn) -> List[Migration]:

    with conn.cursor() as cursor:
        cursor.execute(
            f"select migration_id, up_digest, up, down_digest, down from {migrations_table}"
        )
        rs = cursor.fetchall()
        return [
            Migration(
                migration_id=r[0],
                up_digest=r[1],
                up=r[2],
                down_digest=r[3],
                down=r[4]
            )
            for r in rs
        ]


def get_diff(
    db_migrations: List[Migration],
    file_system_migrations: List[Migration],
    strict_digest_check: bool
) -> Tuple[List[Migration], List[Migration]]:

    first_divergence = None

    for db_migration, file_migration in zip(db_migrations, file_system_migrations):

        if strict_digest_check:
            db_digest = digest(db_migration.up)
            file_digest = digest(file_migration.up)
        else:
            db_digest = db_migration.up_digest
            file_digest = file_migration.up_digest

        if db_digest != file_digest:
            logger.info(f"\nDivergence found at: {db_migration.migration_id}")
            logger.info(f"  DB Migration Digest: {db_digest}")
            logger.info(f"File Migration Digest: {file_digest}")
            first_divergence = db_migration
            break

    if first_divergence:
        old_branch = sorted(
            [
                m for m in db_migrations 
                if m.migration_id >= first_divergence.migration_id
            ],
            key=lambda m: m.migration_id,
            reverse=True,
        )
        new_branch = sorted(
            [
                m for m in file_system_migrations
                if m.migration_id >= first_divergence.migration_id
            ],
            key=lambda m: m.migration_id,
        )

    else:
        old_branch = []

        if not db_migrations:
            max_old_id = 0
        else:
            max_old_id = max(m.migration_id for m in db_migrations)

        new_branch = sorted(
            [m for m in file_system_migrations if m.migration_id > max_old_id],
            key=lambda m: m.migration_id,
        )

    return old_branch, new_branch


def CINE_migrations_table(cursor) -> None:
    try:
        cursor.execute(
            f"""
            create table if not exists {migrations_table} (
                migration_id int      not null primary key,
                up_digest    char(64) not null,
                up           text     not null,
                down_digest  char(64) not null,
                down         text     not null,

                /* meta */
                created_datetime  timestamp not null default now(),
                modified_datetime timestamp not null default now()
            );
                """
        )

    except IntegrityError as e:
        raise RuntimeError("Migrations already in process")


if __name__ == "__main__":
    main()
