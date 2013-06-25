#!/usr/bin/python
# -*- encoding:utf-8 -*-
# 

from storm.locals import Int, Unicode, Reference, Date, Float, ReferenceSet, Desc, Store, Bool
from storm.locals import create_database as storm_create_database

# sqlite> select a.date, a.amount, a.memo, b.account from statement_transaction a, bank_account b
# where a.id_bank_account = b.id_bank_account order by a.id_bank_account, a.date, a.amount;

__all__ = [ 'Category', 'BankAccount', 'LedgerBalance', 'StatementTransaction', 'CategoryRule', 
'create_database', 'execute', 'read_file', 'str2date', 'destroy_database', 'BudgetEntry', 'create_salim_database']

salim_database_statements = '''
CREATE TABLE category (name TEXT PRIMARY KEY, parent_name TEXT);

CREATE TABLE category_rule (id_category_rule INTEGER PRIMARY KEY, category_name TEXT not null, regex TEXT);
CREATE UNIQUE INDEX index_unique_regex ON category_rule ( regex );

CREATE TABLE budget_entry (id_budget_entry INTEGER PRIMARY KEY, category_name TEXT, name TEXT, 
                           date TEXT, amount REAL, scenario TEXT, payed INTEGER);
CREATE TABLE bank_account (account TEXT PRIMARY KEY, bankid INTEGER, name TEXT, branch text, type TEXT );

CREATE TABLE ledger_balance (id_ledger_balance INTEGER PRIMARY KEY, bank_account_name TEXT NOT NULL, date TEXT, 
                             amount REAL );
CREATE UNIQUE INDEX index_unique_balance ON ledger_balance ( bank_account_name, date );

CREATE TABLE statement_transaction (id_statement_transaction INTEGER PRIMARY KEY, id_balance INTEGER, category_name TEXT,
                                    memo TEXT, date TEXT, amount REAL, type TEXT, checknum text, fitid TEXT );
CREATE UNIQUE INDEX index_unique_stmt_trans ON statement_transaction ( fitid );
'''

store = None

def create_database(database_uri):
    """Creates a database base on given URI locator"""
    global store
    if not bool(store):
        store = Store(storm_create_database(database_uri))
    return store

def create_salim_database(database_uri):
    """Create salim database"""
    global salim_database_statements, store
    create_database(database_uri)
    for stmt in salim_database_statements.split(';'):
        store.execute(stmt)
    store.commit()

def destroy_database():
    """docstring for destroy_database"""
    global store
    if not bool(store):
        store.close()
    store = None

def execute(store, statements):
    """Executes sql many statements"""
    if type(statements) is str:
        sql_statements = statements.split(';')
    else:
        sql_statements = iter(statements)
    for stmt in sql_statements:
        # print stmt
        store.execute(stmt)
    store.commit()

def read_file(store, filename):
    '''Loads a database from sql statements of one file'''
    sql_file = file(filename)
    execute(store, sql_file.read())
    sql_file.close()

def str2date(dts):
    '''Converts string 'YYYYMMDD' to date'''
    from datetime import date
    return date( int(dts[0:4]), int(dts[4:6]), int(dts[6:8]) )


class GenericBase(object):
    def _parse_args_and_kwargs(self, *args, **kwargs):
        if bool(args):
            for i,var in enumerate(self.__cons_parms__):
                if len(args) > i:
                    setattr(self, var, args[i])
        if bool(kwargs):
            for var in self.__cons_parms__:
                if kwargs.has_key(var):
                    setattr(self, var, kwargs[var])


class Category(GenericBase):
    __storm_table__ = "category"
    name            = Unicode( primary=True )
    parent_name     = Unicode()
    parent          = Reference( parent_name, name )
    __cons_parms__  = ['name', 'parent']
    
    def __init__(self, *args, **kwargs):
        self._parse_args_and_kwargs(*args, **kwargs)
    
    def add_rule(self, rule):
        result = store.find(CategoryRule, CategoryRule.regex == rule)
        if result.count() == 0:
            return self.rules.add(CategoryRule(rule))
        else:
            return None
    
    @staticmethod
    def by_rule(text):
        import re
        catrs = store.find(CategoryRule)
        for catr in catrs:
            regex = re.compile(catr.regex)
            if bool(regex.search(text)):
                return catr.category
        return None


class CategoryRule(GenericBase):
    __storm_table__ = "category_rule"
    id              = Int(name="id_category_rule", primary=True)
    category_name   = Unicode()
    category        = Reference(category_name, Category.name)
    regex           = Unicode()
    __cons_parms__  = ['regex', 'category']
    
    def __init__(self, *args, **kwargs):
        self._parse_args_and_kwargs(*args, **kwargs)

    @classmethod
    def by_regex(cls, regex):
        return store.find(cls, cls.regex == regex).one()

Category.rules = ReferenceSet(Category.name, CategoryRule.category_name)

class BudgetEntry(GenericBase):
    __storm_table__ = "budget_entry"
    id              = Int( name="id_budget_entry", primary=True )
    category_name   = Unicode()
    category        = Reference( category_name, Category.name )
    name            = Unicode()
    date            = Date()
    amount          = Float()
    payed           = Bool()
    scenario        = Unicode()
    __cons_parms__  = ['name', 'date', 'amount', 'category', 'payed', 'scenario']
    
    def __init__(self, *args, **kwargs):
        self._parse_args_and_kwargs(*args, **kwargs)

    @classmethod
    def find_after_date(cls, date, date_end):
        return store.find( cls, cls.date >= date, cls.date <= date_end ).order_by( cls.date )
    

class BankAccount(GenericBase):
    __storm_table__ = "bank_account"
    account         = Unicode(primary=True)
    bankid          = Int()
    branch          = Unicode()
    type            = Unicode()
    name            = Unicode()
    __cons_parms__  = ['bankid', 'account', 'branch']

    def __init__(self, *args, **kwargs):
        self._parse_args_and_kwargs(*args, **kwargs)        
    

class LedgerBalance(GenericBase):
    __storm_table__   = "ledger_balance"
    id                = Int( name="id_ledger_balance", primary=True )
    bank_account_name = Unicode()
    bank_account      = Reference( bank_account_name, BankAccount.account )
    amount            = Float()
    date              = Date()
    __cons_parms__    = ['date', 'amount', 'bank_account']
    
    def __init__(self, *args, **kwargs):
        self._parse_args_and_kwargs(*args, **kwargs)
        # self.date         = str2date(info['dtasof'])
        # self.amount       = float(info['balamt'])
        # self.bank_account = bank_account
    
    def add_transaction(self, transaction):
        """docstring for add_transaction"""
        if not StatementTransaction.has_fitid(transaction.fitid):
            transaction.balance = self
            transaction.bank_account = self.bank_account
            transaction.category = Category.by_rule(transaction.memo)
            if hasattr(self, '_accum'):
                self._accum += transaction.amount
            else:
                self._accum = transaction.amount
            return transaction
        else:
            return None
        
    def is_valid(self):
        cls = type(self)
        balances = store.find(cls, cls.bank_account == self.bank_account).order_by(Desc(cls.date))
        if balances.count() > 1:
            iter_balances = iter(balances)
            iter_balances.next() # -- discard last balance
            previous_balance = iter_balances.next()
            if hasattr(self, '_accum'):
                a1 = int((previous_balance.amount + self._accum) * 100)
                a2 = int(self.amount * 100)
                return a1 == a2
            else:
                return False
        else:
            return True

    @classmethod
    def previous(cls, date, account):
        balances = store.find( cls, cls.date <= date, cls.bank_account == account).order_by( Desc(cls.date) )
        if balances.count() == 0:
            return None
        else:
            return iter( balances ).next()
    
    @classmethod
    def find_after(cls, balance):
        return ( bal for bal in store.find(cls, cls.date > balance.date, 
            cls.bank_account == balance.bank_account).order_by( cls.date ) )

    @classmethod
    def by_bank_account_and_date(cls, bank_account, date):
        """docstring for by_bank_account_and_date"""
        return store.find(cls, cls.bank_account_name == bank_account.account, cls.date == date).one()

    @classmethod
    def last(cls):
        return iter( store.find(cls).order_by( Desc(cls.date) ) ).next()


class StatementTransaction(GenericBase):
    __storm_table__ = "statement_transaction"
    id              = Int( name="id_statement_transaction", primary=True )
    id_balance      = Int()
    balance         = Reference( id_balance, LedgerBalance.id )
    memo            = Unicode()
    date            = Date()
    amount          = Float()
    type            = Unicode()
    checknum        = Unicode()
    fitid           = Unicode()
    category_name   = Unicode()
    category        = Reference( category_name, Category.name )
    __cons_parms__  = ['date', 'amount', 'memo', 'fitid', 'checknum', 'balance', 'category']

    def __init__(self, *args, **kwargs):
        self._parse_args_and_kwargs(*args, **kwargs)

    @classmethod
    def by_balance(cls, balance):
        return [ s for s in store.find(cls, cls.balance == balance).order_by(cls.date) ]

    @classmethod
    def has_fitid(cls, fitid):
        count = store.find(cls, cls.fitid == fitid).count()
        return count != 0

LedgerBalance.transactions = ReferenceSet(LedgerBalance.id, StatementTransaction.id_balance)
