create table ys (
  y int not null primary key,
  x varchar(32) not null references xs (x)
);

insert into ys (y, x)
     values (1, 'a')
          , (2, 'a')
          , (3, 'b')
          , (4, 'c')
          , (5, 'c')
          , (6, 'c')
          , (7, 'd')
          , (8, 'd');
