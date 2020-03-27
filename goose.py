#!/usr/bin/env python

from argparse import ArgumentParser
from collections import namedtuple
from hashlib import sha256
import os 
from pathlib import PosixPath
from typing import List, Set, Iterable, Optional, T, Tuple

from psycopg2 import connect, OperationalError, IntegrityError, sql
from version import __version__

DBParams = namedtuple('DBParams', 'user password host port database')
Migration = namedtuple('Migration', 'migration_id up down')
Schema = str



def get_migration_id(file_name: str) -> int:
    try:
        return int(file_name[:file_name.index('_')])
    except ValueError:
        print(f'ERROR: File "{file_name}" is not of pattern "(id)_up.sql" or "(id)_down.sql"')
        exit(3)


def get_max_migration_id(filenames: List[str]) -> int:
    return max(
        get_migration_id(file_name)
        for file_name in filenames
    )

def get_migration_files_filtered(dir: PosixPath) -> List[str]:
    return [file for file in os.listdir(dir.as_posix()) if file.lower().endswith('.sql')]

def assert_all_migrations_present(dir: PosixPath) -> None:
    filenames:List[str] = get_migration_files_filtered(dir)
    if not filenames:
        print(f'Migrations folder {dir} is empty. Exiting gracefully!')
        exit(0)

    max_migration_id = get_max_migration_id(filenames)

    for migration_id in range(1, max_migration_id + 1):
        # todo - assertions can be ignored...?
        assert f'{migration_id}_up.sql' in filenames, f'Migration {migration_id} missing ups'
        assert f'{migration_id}_down.sql' in filenames, f'Migration {migration_id} missing downs'
    
    extra_files: Set[str] = (
        set(filenames) 
        - {f'{m_id}_up.sql'   for m_id in range(1, max_migration_id + 1)}
        - {f'{m_id}_down.sql' for m_id in range(1, max_migration_id + 1)}
    )

    if extra_files:
        print('ERROR: Extra files not of pattern "(id)_up.sql" or "(id)_down.sql": ')
        print(*extra_files, sep='\n')
        exit(3)


def parse_migrations(dir: PosixPath) -> List[Migration]:
    filenames:List[str] = get_migration_files_filtered(dir)
    max_migration_id: int = get_max_migration_id(filenames)

    migrations: List[Migration] = [
        parse_migration(dir, migration_id)
        for migration_id in range(1, max_migration_id + 1)
    ]

    return migrations


def parse_migration(dir: PosixPath, migration_id: int) -> Migration:
    up_file:   PosixPath = dir.joinpath(f'{migration_id}_up.sql')
    down_file: PosixPath = dir.joinpath(f'{migration_id}_down.sql')

    with open(up_file) as up_fp, open(down_file) as down_fp:
        migration = Migration(
            migration_id=migration_id,
            up=up_fp.read(),
            down=down_fp.read()
        )
        return migration


def acquire_mutex(cursor) -> None:
    try:
        cursor.execute('''
        /* Ideal lock timeout? */
        SET lock_timeout TO '2s';    

        LOCK TABLE goose_migrations IN EXCLUSIVE MODE;
    ''')
    except OperationalError as e:
        print('Migrations already in progress')
        exit(2)

def set_search_path(cursor, schema: str) -> None:
    cursor.execute(
        sql.SQL(
            'set search_path to {}'.format(schema)
        )
    )

def set_role(cursor, role: str) -> None:
    cursor.execute(
        sql.SQL(
            'set role {}'.format(role)
        )
    )

def main() -> None:
    migrations_directory, db_params, schema, role = _parse_args()

    assert_all_migrations_present(migrations_directory)

    conn = connect(**db_params._asdict())

    with conn:
        cursor = conn.cursor()

        set_search_path(cursor, schema)

        if role is not None:
            set_role(cursor, role)

        CINE_migrations_table(conn.cursor())

        migrations_from_db: List[Migration] = sorted(get_db_migrations(conn), key=lambda m: m.migration_id)
        migrations_from_filesystem: List[Migration] = sorted(parse_migrations(migrations_directory), key=lambda m: m.migration_id)

        old_branch, new_branch = get_diff(migrations_from_db, migrations_from_filesystem)

        acquire_mutex(cursor)

        if old_branch:
            unapply_all(cursor, old_branch)
        apply_all(cursor, new_branch)


def apply_all(cursor, migrations) -> None:
    assert sorted(migrations, key=lambda m: m.migration_id) == migrations, 'Migrations must be applied in ascending order'
    for migration in migrations:
        apply_up(cursor, migration)


def unapply_all(cursor, migrations) -> None:
    assert sorted(migrations, key=lambda m: m.migration_id, reverse=True) == migrations, 'Migrations must be unapplied in descending order'
    for migration in migrations:
        apply_down(cursor, migration)


def apply_up(cursor, migration: Migration) -> None:
    print(migration.migration_id, migration.up, end='\n' * 2)
    cursor.execute(migration.up)
    cursor.execute('''
INSERT INTO goose_migrations (migration_id, up_digest, up, down_digest, down)
     VALUES (%s, %s, %s, %s, %s);
    ''', (migration.migration_id, digest(migration.up), migration.up, digest(migration.down), migration.down,)
    )


def apply_down(cursor, migration: Migration) -> None:
    print(migration.migration_id, migration.down, end='\n' * 2)
    cursor.execute(migration.down)
    cursor.execute('DELETE FROM goose_migrations WHERE migration_id = %s;', (migration.migration_id,))


def _parse_args() -> (PosixPath, DBParams, Schema):
    parser = ArgumentParser()
    parser.add_argument('migrations_directory', help='Path to directory containing migrations')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('-p', '--port', default=5432, type=int)
    parser.add_argument('-U', '--username', default='postgres')
    parser.add_argument('-d', '--dbname', default='postgres')
    parser.add_argument('-s', '--schema', default='public')
    parser.add_argument('-r', '--role', default=None)

    parser.add_argument('-v', '--version', action='version',
                    version='%(prog)s {version}'.format(version=__version__))

    args = parser.parse_args()
    print(args)

    if 'PGPASSWORD' not in os.environ:
        print('PGPASSWORD not set')
        exit(1)
    
    migrations_directory = _get_migrations_directory(args.migrations_directory)

    db_params = DBParams(
        user=args.username,
        password=os.environ['PGPASSWORD'],
        host=args.host,
        port=args.port,
        database=args.dbname
    )
    return migrations_directory, db_params, args.schema, args.role


def _get_migrations_directory(pathname: str) -> PosixPath:
    migrations_directory = PosixPath(pathname).absolute()

    if not migrations_directory.is_dir():
        print(f'ERROR: {migrations_directory.as_posix()} is not a directory')
        exit(1)
    else:
        return migrations_directory


def digest(s: str) -> str:
    return sha256(s.encode('utf-8')).hexdigest()


def first(xs: Iterable[T]) -> Optional[T]:
    try:
        return next(iter(xs))
    except StopIteration:
        return None


def get_db_migrations(conn) -> List[Migration]:
    with conn:
        # todo - namedtuple cursor
        with conn.cursor() as cursor:
            cursor.execute('select migration_id, up_digest, up, down_digest, down from goose_migrations')
            rs = cursor.fetchall() 
            return [
                    Migration(
                    migration_id = r[0],
                    up = r[2],
                    down = r[4]
                )
                for r in rs
            ]


def get_diff(db_migrations: List[Migration], file_system_migrations: List[Migration]) -> Tuple[List[Migration], List[Migration]]:
    first_divergence: Optional[Migration] = first(
        db_migration
        for db_migration, fs_migration in zip(db_migrations, file_system_migrations)
        if digest(db_migration.up) != digest(fs_migration.up)
    )

    if first_divergence:
        old_branch = sorted(
            [m for m in db_migrations if m.migration_id >= first_divergence.migration_id],
            key=lambda m: m.migration_id,
            reverse=True
        )
        new_branch = sorted(
            [m for m in file_system_migrations if m.migration_id >= first_divergence.migration_id],
            key=lambda m: m.migration_id
        )
        return old_branch, new_branch
    else:
        old_branch = []
        max_old_id = 0 if not db_migrations else max(m.migration_id for m in db_migrations)
        new_branch = sorted(
            [m for m in file_system_migrations if m.migration_id > max_old_id],
            key=lambda m: m.migration_id
        )
        return old_branch, new_branch


def CINE_migrations_table(cursor) -> None:
    try:
        cursor.execute('''
    create table if not exists goose_migrations (
        migration_id int      not null primary key,
        up_digest    char(64) not null,
        up           text     not null,
        down_digest  char(64) not null,
        down         text     not null,

        /* meta */
        created_datetime  timestamp not null default now(),
        modified_datetime timestamp not null default now()
    );
        ''')
    except IntegrityError as e:
        print('Migrations already in process')
        exit(4)


if __name__ == '__main__':
    main()
