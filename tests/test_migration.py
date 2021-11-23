# Run this script like so: PYTHONPATH=. pytest --postgresql-port=32777 --postgresql-password=mysecretpassword -rP
import os
import time

import pytest
from pytest_postgresql import factories

from goose import run_migrations, DBParams

postgresql_in_docker = factories.postgresql_noproc(
    dbname='test_db', load=['tests/setup/create-schema.sql'])
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


def test_migrations(db_params):
    """Run migrations"""
    schema = 'schema_1'
    migrations_directory = 'tests/branch_migrations'
    print(db_params)
    run_migrations(
        migrations_directory,
        db_params,
        schema
    )
    # cur = postgresql.cursor()
    # cur.execute(
    #     "CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);"
    # )
    # postgresql.commit()
    breakpoint()
