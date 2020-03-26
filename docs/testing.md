## Testing on local machine

* Checkout the repository
   ```bash
   git clone https://github.com/sasidhar/postgoose.git
   ```
* Create another folder for testing
  ```bash
  mkdir test-postgoose
  ```
* Create a virtual environemnt
  ```bash
  cd test-postgoose
  python3 -m venv .venv
  source .venv/bin/activate
  ```
* Install postgoose from the checkedout repository folder
  ```bash
  pip install -e ../postgoose
  ```
* Goose is ready to use from this virtual environment
  ```bash
  goose --version
  ```
* Run postgres in a docker container
  ```bash
  docker container run \
    --name test-postgres \
    -e POSTGRES_PASSWORD=top-secret \
    -p 54320:5432 \
    -d \
    postgres:10
  ```
* Create base database, users and roles
  ```bash
  # Hope you have psql available on your local machine
  PGPASSWORD=top-secret \
    psql \
    -v ON_ERRO_STOP=1 \
    -U postgres \
    -h 127.0.0.1 \
    -p 54320 \
    postgres \
    -a -f ../postgoose/tests/setup/create-database-users-roles.sql

  # Checkout `create-database-users-roles.sql` file for more details
  ```
* Create schema
  ```bash
  PGPASSWORD=top-secret-admin-user \
    psql \
    -v ON_ERRO_STOP=1 \
    -U user_admin \
    -h 127.0.0.1 \
    -p 54320 \
    test_db \
    -a -f ../postgoose/tests/setup/create-schema.sql

  # Checkout `create-schema.sql` file for more details
  ```
* Run migrations
  ```bash
  PGPASSWORD=top-secret-admin-user \
    goose \
    --host 127.0.0.1 \
    -p 54320 \
    -U user_admin \
    -d test_db \
    -s schema_1 \
    -r role_admin \
    ../postgoose/tests/branch_migrations
  ```
* Validate migrations
  ```bash
  # List Tables in Schema
  PGPASSWORD=top-secret-admin-user \
    psql \
    -v ON_ERRO_STOP=1 \
    -U user_admin \
    -h 127.0.0.1 \
    -p 54320 \
    test_db \
    -c "SELECT schemaname, tablename, tableowner FROM pg_tables where schemaname='schema_1'"

  # List rows from goose_migrations table
  PGPASSWORD=top-secret-admin-user \
    psql \
    -v ON_ERRO_STOP=1 \
    -U user_admin \
    -h 127.0.0.1 \
    -p 54320 \
    test_db \
    -c "SELECT migration_id, up_digest, down_digest, created_datetime, modified_datetime FROM schema_1.goose_migrations"
  ```
* Clean up postgres docker container
  ```
  docker container \
    stop test-postgres \
    && \
    docker container \
    rm test-postgres
  ```

