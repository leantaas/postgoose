![](http://wildgoosefestival.org/wp-content/uploads/2014/06/wild-goose-in-action.jpg)

# SQL migrations for Postgres

```
PGPASSWORD=top-secret goose ./tests/master_migrations  
```
(Assuming you have a Postgres server running on `localhost:5432` with a high-entropy admin password)

## Installation
```
pip install postgoose
```

## Usage

```
usage: goose [-h] [--host HOST] [-p PORT] [-U USERNAME] [-d DBNAME] [-s SCHEMA] [-r ROLE] [-v] migrations_directory

positional arguments:
  migrations_directory  Path to directory containing migrations

optional arguments:
  -h, --help            show this help message and exit
  --host HOST
  -p PORT, --port PORT
  -U USERNAME, --username USERNAME
  -d DBNAME, --dbname DBNAME
  -s SCHEMA, --schema SCHEMA
  -r ROLE, --role ROLE
  -v, --version         show program's version number and exit
```

Where `migrations_directory` is some directory of form:
```
./migrations
  1_up.sql
  1_down.sql
  2_up.sql
  2_down.sql
  3_up.sql
  3_down.sql
```

Current main difference from Play Framework migrations is that a migration in Goose is all-or-nothing.

E.g. you are on master branch on revision 5 and want to switch to a feature branch whose latest revision is 4'.
```
1 <- 2 <- 3 <- 4 <- 5  
       \
         3' <- 4' 
```
Applying migrations through Goose will leave you on either revision 5 (if an error is encountered) or revision 4' (if migration is successful) but not on any of 4, 3, 2, or 3'. 

## Testing on local machine

  * Check `docs/testing.md`

## License

Copyright 2018 LeanTaas, Inc. 

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
