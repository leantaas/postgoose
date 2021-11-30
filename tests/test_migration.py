# Run this script like so: PYTHONPATH=. pytest --postgresql-port=32777 --postgresql-password=mysecretpassword -rP
# TODO: Apply migrations without making that a param in tests
# TODO: Add a command line based test to verify parameter handling
# TODO: Add readme for postgresql database instance suggestions (Docker-compose)
import os
import time

import pytest
from pytest_postgresql import factories

from goose import run_migrations, DBParams

postgresql_in_docker = factories.postgresql_noproc(dbname='test_db')
postgresql = factories.postgresql("postgresql_in_docker", dbname='test_db')


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


@pytest.fixture
def apply_master_migrations(db_params, verbose, auto_apply_down, strict_digest_check):
    """Run migrations"""
    migrations_directory = 'tests/master_migrations'
    run_migrations(
        migrations_directory,
        db_params,
        auto_apply_down=auto_apply_down,
        verbose=verbose,
        strict_digest_check=strict_digest_check
    )

@pytest.fixture
def apply_branch_migrations(db_params, verbose, auto_apply_down, strict_digest_check, postgresql):
    """Run migrations twice to apply up and down"""

    run_migrations(
        'tests/branch_migrations',
        db_params,
        auto_apply_down=auto_apply_down,
        verbose=verbose,
        strict_digest_check=strict_digest_check
    )
    run_migrations(
        'tests/branch_migrations2',
        db_params,
        auto_apply_down=True,
        verbose=verbose,
        strict_digest_check=strict_digest_check
    )


def test_xs_migrations(apply_master_migrations, postgresql):
    with postgresql.cursor() as cur:
        cur.execute('SELECT * FROM xs;')
        response = cur.fetchall()
        assert response == [('a',), ('b',), ('c',), ('d',)]


def test_ys_migrations(apply_branch_migrations, postgresql):
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
