----
-- phpLiteAdmin database dump (http://www.phpliteadmin.org/)
-- phpLiteAdmin version: 1.9.7.1
-- Exported: 5:18am on December 6, 2021 (UTC)
-- database file: /home/ubuntu/pset9/finance/finance.db
----

----
-- Drop table for users
----
DROP TABLE IF EXISTS "users";

----
-- Table structure for users
----
CREATE TABLE users (id INTEGER, username TEXT NOT NULL, hash TEXT NOT NULL, cash NUMERIC NOT NULL DEFAULT 10000.00, PRIMARY KEY(id));

----
-- Drop table for portfolios
----
DROP TABLE IF EXISTS "portfolios";

----
-- Table structure for portfolios
----
CREATE TABLE 'portfolios' ('id' integer PRIMARY KEY AUTOINCREMENT NOT NULL,'symbol' text NOT NULL, 'shares' integer NOT NULL, 'user_id'  INTEGER NOT NULL  );

----
-- Drop table for transactions
----
DROP TABLE IF EXISTS "transactions";

----
-- Table structure for transactions
----
CREATE TABLE 'transactions' ('id' integer PRIMARY KEY AUTOINCREMENT NOT NULL,'timestamp' timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, 'shares' integer NOT NULL, 'symbol' text NOT NULL, 'user_id'  INTEGER NOT NULL  , 'price'  INTEGER NOT NULL  );

----
-- Drop index for username
----
DROP INDEX IF EXISTS "username";

----
-- structure for index username on table users
----
CREATE UNIQUE INDEX username ON users (username);

----
-- Drop index for transaction_user_id_idx
----
DROP INDEX IF EXISTS "transaction_user_id_idx";

----
-- structure for index transaction_user_id_idx on table transactions
----
CREATE INDEX 'transaction_user_id_idx' ON "transactions" ("user_id");

----
-- Drop index for portfolios_user_id_idx
----
DROP INDEX IF EXISTS "portfolios_user_id_idx";

----
-- structure for index portfolios_user_id_idx on table portfolios
----
CREATE INDEX 'portfolios_user_id_idx' ON "portfolios" ("user_id");
