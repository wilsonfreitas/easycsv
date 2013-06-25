#!/usr/bin/env python
# encoding: utf-8
#

"""
easycsv.py

The easycsv module executes csv statements (a kind of csv DSL - domain 
specific language) to insert/update/delete data into a database.

Easycsv was developed to be used with the Storm ORM framework, but it 
could be easily adapted for others ORM frameworks (SQLAlchemy, SQLObject, ...).

>>> from storm.locals import *
>>>
>>> class Category(object):
...     __storm_table__ = 'category'
...     name = Unicode(primary=True)
...     parent_name = Unicode()
...     parent = Reference(parent_name, name)
... 
>>>
>>> database = create_database('sqlite:')
>>> store = Store(database)
>>> store.execute('CREATE TABLE category (name TEXT PRIMARY KEY, parent_name TEXT)')
<storm.databases.sqlite.SQLiteResult object at 0xa8a790>
>>> 
>>> from easycsv import StormORM
>>> 
>>> statements = '''\
... Category, Name, Parent
... +, Expenses,
... +, Internet, Expenses
... '''
>>> 
>>> orm = StormORM(store=store)
>>> orm.execute(statements, modName='__main__')
(2, 0, 0, 2)

This session creates the table Category using the storm framework and inserts
two rows into the database.
The tuple returned from orm.execute says that two statements were submitted and
two rows were inserted.

The variable defines one csv statement block. A csv statement block has a
header that starts with the name of the class followed by some of its attributes.
The lines starting with '+' represent the csv statements, in particular, csv 
insert statements.
There are three types of csv statements:
    - '+' insert
    - '-' delete
    - '~' update

Lines starting with '#', with the first column empty and empty lines are ignored.

Copyright (c) 2008. All rights reserved.
"""

import csv
import re

from datetime  import date
from itertools import count
from operator  import attrgetter, and_, eq
from types     import MethodType

__all__ = ['INSERT', 'DELETE', 'UPDATE', 'AttributeParser', 'StormAttributeParser', 
           'simple', 'camelCase', 'CSV', 'CSVType', 'CSVStatement', 'StormORM', 'ORM']

INSERT = '+'
DELETE = '-'
UPDATE = '~'


class AttributeParser(object):
    """
    Generic parser applied to column fields of a statements block.
    The methods used to parse column fields start with parse and receives two parameters:
    text to be parsed and match object of re module.
    """
    def __init__(self):
        self.regexes = self.__createMethodAnalyzers()
        
    def __createMethodAnalyzers(self):
        pairs = []
        for methodName in dir(self):
            method = getattr(self, methodName)
            if methodName.startswith('parse') and type(method) is MethodType and method.__doc__:
                pairs.append( (re.compile(method.__doc__), method) )
        return pairs
    
    def parse(self, text):
        '''
        Parse text elements according to its own parserXXX methods or
        those created in child classes.
        
        @param text: text to be parsed
        
        @return: parsed value of text
        '''
        result = None
        for regex, func in self.regexes:
            match = regex.match(text)
            if match:
                result = func(text, match)
                break
        if result is None:
            result = self.parseAny(text)
        return result
    
    def parseNumber(self, text, match):
        r'^-?\s*\d+([\.,]\d+)?$'
        return eval(text)
    
    def parseBoolean(self, text, match):
        r'^[Tt][Rr][Uu][eE]|[Ff][Aa][Ll][Ss][Ee]$'
        return eval(text.lower().capitalize())
    
    def parseText(self, text, match):
        r'^\''
        return text[1:]
    
    def parseAny(self, text):
        return text
    

class StormAttributeParser(AttributeParser):
    """
    Implementation of parser for storm ORM. It generates unicode strings and
    parses dd-mm-yyyy to datetime.date objects.
    """
    def __init__(self):
        super(StormAttributeParser, self).__init__()
    
    def parseText(self, text, match):
        r'^\''
        s = text[1:]
        s.decode('utf-8')
        return unicode(s)
    
    def parseDate(self, text, match):
        r'^\d?\d[/.-]\d\d[/.-]\d\d\d\d$'
        # dsr -- date separator regex
        dsr = re.compile(r'[/.-]')
        # dp -- date parts
        dp = dsr.split(text)
        return date( int(dp[2]), int(dp[1]), int(dp[0]) )
    
    def parseAny(self, text):
        return unicode(text.decode('utf-8'))
    

def simple(attrName):
    '''
    Convert human readable header names to property names in lower case and 
    replacing spaces to underscore.
    Examples:

    >>> simple("Category")
    "category"
    >>> simple("Bank Account")
    "bank_account"
    '''
    attrName = str(attrName).strip()
    attrName = attrName.lower()
    attrName = re.sub('\s+', '_', attrName)
    return attrName


def camelCase(attrName):
    '''
    Convert human readable header names to camel case property names.
    Examples:

    >>> camelCase("Category")
    'category'
    >>> camelCase("Bank Account")
    'bankAccount'
    '''
    attrParts = attrName.lower().split()
    s = []
    for i,part in enumerate(attrParts):
        if i == 0:
            s.append(part)
        else:
            s.append(part.capitalize())
    return ''.join(s)
    


class CSV(object):
    """CSV class that handles the csv files
    content is any iterable where the content of each row is data delimited text.
    """
    def __init__(self, content, attrParser=AttributeParser(), modName=None, module=None, nameResolution=simple):
        '''
        @param content: The csv content in one of following types: str, file or any iterable that iterate over csv lines.
        @param attrParser: Any class that inherits AttributeParser.
        @param modName: The name of the module where classes declared in the header of a statement block.
        @param module: the module where classes declared in the header of a statement block.
        @param nameResolution: The function used to resolve the column's names in the header of a statement block.
        '''
        if type(content) is str:
            import os
            content = content.split(os.linesep)
        
        self.types = []
        for i, csvRow in enumerate(csv.reader(content)):
            csvRow = [f.strip() for f in csvRow]
            if len(csvRow) is 0 or csvRow[0] in ['#', '']:
                continue
            elif csvRow[0] in '+-~':
                statement = CSVStatement(csvRow, attrParser)
                statement.lineNumber = i+1
                statement.lineContent = ','.join(csvRow)
                csvType.addStatement( statement )
            elif csvRow[0][0].isalpha():
                csvType = CSVType(csvRow, nameResolution=nameResolution, modName=modName, module=module)
                csvType.lineNumber = i+1
                csvType.lineContent = ','.join(csvRow)
                self.types.append(csvType)
    


class CSVType(object):
    """
    The CSVType declared at the header of a csv statement block.
    """
    def __init__(self, fields, nameResolution=simple, modName=None, module=None):
        '''
        @param fields: A list with the fields of a row in a csv file.
        @param modName: The name of the module where classes declared in the header of a statement block.
        @param module: the module where classes declared in the header of a statement block.
        @param nameResolution: The function used to resolve the column's names in the header of a statement block.
        '''
        self.typeName = fields[0]
        self.type = importClass(self.typeName, modName=modName, module=module)
        self.keys = {}
        self.attributes = {}
        self.statements = []
        self.hasPrimaryKey = False
        self.primaryKey = None
                
        for i, field in zip(count(1), fields[1:]):
            field = nameResolution(field)
            if re.match(r'^\{[^\{\}]+\}$', field):
                field = field.strip('{}')
                self.keys[i] = field
            else:
                self.attributes[i] = field
            if isPrimaryKey(self.type, field):
                self.primaryKey = (i, field)
                if i in self.keys:
                    self.hasPrimaryKey = True
        if len(self.keys) is 0 and self.primaryKey:
            # if self.primaryKey is None:
            #     raise Exception("No key given")
            # else:
            self.keys[ self.primaryKey[0] ] = self.primaryKey[1]
            self.hasPrimaryKey = True
            if self.primaryKey[0] in self.attributes:
                del self.attributes[ self.primaryKey[0] ]
    
    def addStatement(self, statement):
        self.statements.append(statement)
    


class CSVStatement(object):
    """
    CSVStatement represents the csv statement to be executed by a ORM.
    """
    def __init__(self, csvRow, attrParser):
        '''
        @param csvRow: A list with the splited content of a text csv row.
        @param attrParser: Any class that inherits AttributeParser.
        '''
        self.action = csvRow[0]
        self.csvRow = csvRow
        self.attributes = {}
        for i, field in zip(count(1), csvRow[1:]):
            self.attributes[i] = attrParser.parse(field)
    


class ORM(object):
    """The ORM engine super class."""
    def execute(self, csv, attrParser=None, modName=None, module=None, nameResolution=simple):
        """
        Creates the CSV object with csv types and csv statements and sends the CSV to be executed
        by the proper ORM.
        
        @param attrParser: Any class that inherits AttributeParser.
        @param modName: The name of the module where classes declared in the header of a statement block.
        @param module: the module where classes declared in the header of a statement block.
        @param nameResolution: The function used to resolve the column's names in the header of a statement block.
        
        @return: Return a 4-tuple that indicates:
            - total rows inserted
            - total rows updated
            - total rows deleted
            - total statements sent
        following this order.
        """
        
        if not attrParser:
            attrParser = self.attrParser
            
        if type(csv) is not CSV:
            csv = CSV(csv, attrParser=attrParser, modName=modName, module=module, nameResolution=nameResolution)
        
        return self._execute(csv)
            
    def _execute(self, csv):
        """Executes all statements of a CSV object.
        
        @param csv: CSV object.
        """
        i, d, u, t = 0, 0, 0, 0
        for typo in csv.types:
            for statement in typo.statements:
                try:
                    n = self.executeStatement(typo, statement)
                    t += n
                    if statement.action is INSERT:
                        i += n
                    elif statement.action is UPDATE:
                        u += n
                    elif statement.action is DELETE:
                        d += n
                except ValueError, ex:
                    print ex
        return i, u, d, t



class StormORM(ORM):
    """
    Storm implementation of ORM super class.
    """
    def __init__(self, uri=None, store=None):
        '''
        @param uri: Database URI following storm rules.
        @param store: Storm store.
        
        If uri is given a new store is instanciated and it is used 
        to execute the statements.
        If both parameters are given the early created store overrides
        the store given.
        '''
        from storm.locals import create_database, Store
        self.uri = uri
        self.store = store
        if self.uri:
            database = create_database(self.uri)
            self.store = Store(database)
        if not self.store:
            raise Exception('None storm store')
        self.attrParser = StormAttributeParser()
            
    def _getObject(self, csvType, csvStatement):
        """
        Retrieves the object to be used at statement execution.
        
        @param csvType: The CSVType
        @param csvStatement: The CSVStatement
        
        @return: The object early instanciated (for insert statement) or
        retrieved from database (for update or delete statements).
        """
        typo = csvType.type
        keys = csvType.keys
        attributes = csvStatement.attributes
        if csvStatement.action in [DELETE, UPDATE]:
            if csvType.hasPrimaryKey:
                return self.store.get(typo, attributes[ csvType.primaryKey[0] ])
            else:
                pred = And([Eq(typo, key, attributes[i]) for i,key in keys.iteritems()])
                result = self.store.find(typo, pred)
                if result.count() == 0:
                    return None
                elif result.count() == 1:
                    return result.one()
                else:
                    return [r for r in result]
        elif csvStatement.action is INSERT:
            return typo()
    
    def executeStatement(self, csvType, csvStatement):
        """
        Executes csv statements matched by the pair csvType, csvStatement.
        
        @param csvType: The CSVType
        @param csvStatement: The CSVStatement
        
        @return: Total statements executed or raises a ValueError if the object retrieved with
        the pair csvType, csvStatement is None.
        """
        obj = self._getObject(csvType, csvStatement)
        
        if not obj:
            msg = 'Statement return None in line %d: %s' % (csvStatement.lineNumber, csvStatement.lineContent)
            raise ValueError(msg)
            
        objs = []
        
        if type(obj) is list:
            objs += obj
        else:
            objs.append(obj)
            
        i = 0
        for _obj in objs:
            self._executeStatement(_obj, csvType, csvStatement)
            i += 1
            
        return i
    
    def _executeStatement(self, obj, csvType, csvStatement):
        """
        Executes a single csv statement
        
        @param csvType: The CSVType
        @param csvStatement: The CSVStatement
        """
        keys = csvType.keys
        attributes = csvType.attributes
        values = csvStatement.attributes
        if csvStatement.action is INSERT:
            pairs = [(key, values[i]) for i,key in keys.iteritems()]
            pairs += [(key, values[i]) for i,key in attributes.iteritems()]
            for key, value in pairs:
                setattr(obj, key, value)
            self.store.add(obj)
        elif csvStatement.action is UPDATE:
            pairs = [(key, values[i]) for i,key in attributes.iteritems()]
            for key, value in pairs:
                setattr(obj, key, value)
        elif csvStatement.action is DELETE:
            self.store.remove(obj)
        self.store.commit()
    


# class SQLObjectORM(ORM):
#     """TODO: implement SQLObject Adaptor"""
#     def __init__(self, arg):
#         super(SQLObjectORM, self).__init__()
#         self.arg = arg
#     
# 
# 
# class SQLAlchemyORM(ORM):
#     """TODO: implement SQLAlchemy Adaptor"""
#     def __init__(self, arg):
#         super(SQLAlchemyORM, self).__init__()
#         self.arg = arg
    


def importClass(className, modName=None, module=None):
    if not module:
        if not modName:
            fields = className.split('.')
            modName = '.'.join(fields[:-1])
            className = fields[-1]
        # module = __import__(modName) # doesnt work
        module = __import__(modName, globals(), locals(), [className], -1)
    return getattr(module, className)


def isPrimaryKey(cls, attrName):
    attr = getattr(cls, attrName)
    if hasattr(attr, 'primary') and attr.primary:
        return True
    else:
        return False


def Eq(cls, name, value):
    f = attrgetter(name)
    return eq(f(cls), value)


def And(preds):
    return reduce(and_, preds)

