# Run this script like so: PYTHONPATH=. pytest --postgresql-port=32777 --postgresql-password=mysecretpassword -rP
# TODO: Add test for empty down files
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
def apply_migrations(db_params):
    """Run migrations"""
    migrations_directory = 'tests/branch_migrations'
    run_migrations(
        migrations_directory,
        db_params
    )
    # cur = postgresql.cursor()
    # cur.execute(
    #     "CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);"
    # )
    # postgresql.commit()


def test_xs_migrations(apply_migrations, postgresql):
    cur = postgresql.cursor()
    cur.execute('SELECT * FROM xs;')
    response = cur.fetchall()
    assert response == [('a',), ('b',), ('c',), ('d',)]
    cur.close()


def test_ys_migrations(apply_migrations, postgresql):
    cur = postgresql.cursor()
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
    cur.close()
