from dataclasses import dataclass

from app_logger import get_app_logger

logger = get_app_logger()


@dataclass
class DBParams:
    user: str
    password: str
    host: str
    port: int
    database: str


@dataclass
class Migration:
    migration_id: int
    up_digest: str
    up: str
    down_digest: str
    down: str


def print_args(args_object):

    args_dict = vars(args_object)

    print("\nArguments: ")
    for key, value in args_dict.items():
        print(f"   {key:>22} : {value}")


def print_up_down(verbose, migration, migration_type) -> None:

    migration_id = getattr(migration, "migration_id")

    print(f"\nMigration ID: {migration_id}")
    print(f"Migration Type: {migration_type}")

    if verbose:
        migration = getattr(migration, migration_type)
        print("Migrations:")
        print(migration)
