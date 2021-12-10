BEGIN TRANSACTION;
DROP TABLE IF EXISTS "users";
CREATE TABLE "users" (
	"id"		INTEGER,
	"username"	TEXT NOT NULL,
	"hash"		TEXT NOT NULL,
	"cash"		NUMERIC NOT NULL DEFAULT 10000.00,
	PRIMARY KEY("id")
);
DROP TABLE IF EXISTS "portfolios";
CREATE TABLE "portfolios" (
	"id"		integer NOT NULL,
	"shares"	integer NOT NULL,
	"symbol"	text NOT NULL,
	"user_id"	REFERENCES users ("id") ON UPDATE CASCADE ON DELETE CASCADE NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "transactions";
CREATE TABLE "transactions" (
	"id"		integer NOT NULL,
	"timestamp"	timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"shares"	integer NOT NULL,
	"symbol"	text NOT NULL,
	"price"		INTEGER NOT NULL,
	"user_id" 	REFERENCES users ("id") ON UPDATE CASCADE ON DELETE CASCADE NOT NULL,
	"portfolio_id" 	REFERENCES portfolios ("id") ON UPDATE CASCADE ON DELETE SET NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP INDEX IF EXISTS "portfolios_user_id_idx";
CREATE INDEX "portfolios_user_id_idx" ON "portfolios" (
	"user_id"
);
DROP INDEX IF EXISTS "transactions_user_id_idx";
CREATE INDEX "transactions_user_id_idx" ON "transactions" (
	"user_id"
);
DROP INDEX IF EXISTS "transactions_timestamp_idx";
CREATE INDEX "transactions_timestamp_idx" ON "transactions" (
	"timestamp"
);
DROP INDEX IF EXISTS "username";
CREATE UNIQUE INDEX "username" ON "users" (
	"username"
);
COMMIT;
