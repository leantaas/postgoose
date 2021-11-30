# TODO: Add a command line based test to verify parameter handling
import os

import pytest
from pytest_postgresql import factories

from goose import run_migrations, DBParams

postgresql_in_docker = factories.postgresql_noproc(dbname='pytest_db')
postgresql = factories.postgresql("postgresql_in_docker", dbname='pytest_db')


@pytest.fixture
def db_params(postgresql):
    db_params = DBParams(
        user=postgresql.info.user,
        password=postgresql.info.password,
        host=postgresql.info.host,
        port=postgresql.info.port,
        database=postgresql.info.dbname
    )
    return db_params


def test_xs_migrations(
    db_params,
    auto_apply_down,
    strict_digest_check,
    verbose,
    postgresql
):
    migrations_directory = 'tests/master_migrations'
    run_migrations(
        migrations_directory,
        db_params,
        auto_apply_down=auto_apply_down,
        verbose=verbose,
        strict_digest_check=strict_digest_check
    )

    with postgresql.cursor() as cur:
        cur.execute('SELECT * FROM xs;')
        response = cur.fetchall()
        assert response == [('a',), ('b',), ('c',), ('d',)]


def test_up_down_migrations(
    db_params,
    verbose,
    auto_apply_down,
    strict_digest_check, 
    postgresql
):
    """Run migrations twice to apply up and down"""

    run_migrations(
        'tests/branch_migrations',
        db_params,
        auto_apply_down=auto_apply_down,
        verbose=verbose,
        strict_digest_check=strict_digest_check
    )

    run_migrations(
        'tests/modified_branch_migrations',
        db_params,
        auto_apply_down=True,
        verbose=verbose,
        strict_digest_check=strict_digest_check
    )

    with postgresql.cursor() as cur:
        cur.execute('SELECT * FROM ys;')
        response = cur.fetchall()
        assert response == [
            (1, 'a'),
            (2, 'a'),
            (3, 'b'),
            (4, 'c'),
            (5, 'c'),
            (6, 'c'),
            (7, 'd'),
            (8, 'd')
        ]

def test_cmd_migrations(
    db_params,
    verbose,
    auto_apply_down,
    strict_digest_check,
    postgresql
):
    return_code = os.system(f'''
        goose {db_params}{" --verbose" if verbose else ''}{" --no_strict_digest_check" if not strict_digest_check else ''}{" --auto_apply_down" if auto_apply_down else ''} \
            ./tests/branch_migrations
    ''')
    assert return_code == 0
    with postgresql.cursor() as cur:
        cur.execute('SELECT * FROM ys;')
        response = cur.fetchall()
        assert response == [
            (1, 'a'),
            (2, 'a'),
            (3, 'b'),
            (4, 'c'),
            (5, 'c'),
            (6, 'c'),
            (7, 'd')
        ]
