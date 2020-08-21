def str_to_bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def print_args(args_object):

    args = args_object.__dict__

    print("\nArguments: ")
    for arg in args:
        print(f"   {arg:>22} : {args[arg]}")


def print_up_down(verbose, migration, migration_type) -> None:

    migration_id = getattr(migration, "migration_id")

    print(f"\nMigration ID: {migration_id}")
    print(f"Migration Type: {migration_type}")

    if verbose:
        migration = getattr(migration, migration_type)
        print("Migrations:")
        print(migration)
