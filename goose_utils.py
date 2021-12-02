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

    def __str__(self):
        return ' '.join(
            f'--{param}={value}' for param, value in vars(self).items()
        )


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


def print_up_down(migration, migration_type) -> None:

    logger.info(f"\nMigration ID: {getattr(migration, 'migration_id')}")
    logger.info(f"Migration Type: {migration_type}")

    logger.debug(f"Migrations:\n")
    for key, value in vars(migration).items():
        logger.debug(f'{key}={value}')
