-- BEGIN TRANSACTION;

CREATE TABLE category (
                   name TEXT PRIMARY KEY,
                   parent_name TEXT
                   );

INSERT INTO "category" VALUES('Filhos', NULL);
INSERT INTO "category" VALUES('Automóvel', NULL);
-- INSERT INTO "category" VALUES('Despesas Operacionais', NULL);
INSERT INTO "category" VALUES('Empregada', NULL);
INSERT INTO "category" VALUES('Despesas São Paulo', NULL);
INSERT INTO "category" VALUES('Receitas', NULL);

CREATE TABLE category_rule (
id_category_rule INTEGER PRIMARY KEY,
category_name TEXT not null,
regex TEXT);

CREATE UNIQUE INDEX index_unique_regex ON category_rule ( regex );

CREATE TABLE budget_entry (
                   id_budget_entry INTEGER PRIMARY KEY,
                   category_name TEXT,
                   name TEXT,
                   date TEXT,
                   amount REAL, scenario TEXT, payed INTEGER );

CREATE TABLE bank_account (
account text primary key,
bankid integer,
name text,
branch text,
type text );

-- CREATE UNIQUE INDEX index_unique_bank_account ON bank_account ( bankid, account );

CREATE TABLE ledger_balance (
id_ledger_balance integer primary key,
bank_account_name text not null,
date text,
amount real );

CREATE UNIQUE INDEX index_unique_balance ON ledger_balance ( bank_account_name, date );

CREATE TABLE statement_transaction (
id_statement_transaction integer primary key,
id_balance integer,
category_name text,
memo text,
date text,
amount real,
type text,
checknum text,
fitid text );

CREATE UNIQUE INDEX index_unique_stmt_trans ON statement_transaction ( fitid );
-- CREATE UNIQUE INDEX index_unique_stmt_trans_valitation ON statement_transaction ( id_bank_account, memo, date, amount  );

