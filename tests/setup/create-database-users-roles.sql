create database test_db;

create user user_admin with password 'top-secret-admin-user';
create user user_read_only with password 'top-secret-read-only-user';

begin transaction;

    create role role_admin;
    create role role_read_only;

    grant role_admin to user_admin;
    grant role_read_only to user_read_only;

    grant role_read_only to role_admin;

    revoke all on database test_db from public;

    grant connect on database test_db to role_read_only;
    grant create on database test_db to role_admin;

commit;

alter role role_read_only nosuperuser nocreatedb nocreaterole;

