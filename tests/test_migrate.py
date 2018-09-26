import os

# need helper method for asserting existence of tables in database

def test_migrate():
    # import pdb; pdb.set_trace()
    return_code = os.system('''
        PGPASSWORD=top-secret ./goose ./tests/branch_migrations
    ''')
    assert return_code == 0