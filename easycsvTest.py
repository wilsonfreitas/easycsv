#!/usr/bin/python
# -*- encoding: latin1 -*-

import sys

from unittest import TestCase, TestSuite, makeSuite, TextTestRunner
from model import *
from datetime import date
import model

from easycsv import *


class TestStormORM(TestCase):
    """docstring for TestStormORM"""
    
    csvAddContent = '''
model.Category,Name, Parent
+             ,Casa,
+             ,Contas, Casa
+             ,Despesas Operacionais, Casa
'''.split('\n')
    
    csvUpdateContent = '''
model.Category,Name
+                   ,Casa
+                   ,SP

model.Category,Name, Parent
+                   ,Contas, Casa
+                   ,Despesas Operacionais, Casa

model.Category,Name, Parent
~                   ,Despesas Operacionais, SP
'''.split('\n')
    
    csvDeleteContent = '''
model.Category,Name, Parent
-                   ,Despesas Operacionais, Casa
'''.split('\n')
    
    def setUp(self):
        """docstring for setUp"""
        self.store = create_database('sqlite:')
        read_file(self.store, 'salim.sql')
        
    def tearDown(self):
        """docstring for tearDown"""
        destroy_database()
        
    def test_1_Insert(self):
        """testing Insert"""
        csv = CSV(self.csvAddContent, attrParser=StormAttributeParser())
        storm = StormORM(store=self.store)
        storm.execute(csv)
        cat = self.store.get(Category, u'Casa')
        self.assertEqual(cat.name, u'Casa')
        
        cat = self.store.get(Category, u'Contas')
        self.assertEqual(cat.parent.name, u'Casa')
        
    def test_2_Update(self):
        """testing Update"""
        csv = CSV(self.csvUpdateContent, attrParser=StormAttributeParser())
        storm = StormORM(store=self.store)
        storm.execute(csv)
        cat = self.store.get(Category, u'SP')
        self.assertEqual(cat.name, u'SP')
        
        cat = self.store.get(Category, u'Despesas Operacionais')
        self.assertEqual(cat.parent.name, u'SP')
        
    def test_3_Delete(self):
        """testing Delete"""
        csv = CSV(self.csvAddContent, attrParser=StormAttributeParser())
        storm = StormORM(store=self.store)
        storm.execute(csv)
        
        cat = self.store.get(Category, u'Despesas Operacionais')
        self.assertEqual(cat.parent.name, u'Casa')
        
        csv = CSV(self.csvDeleteContent, attrParser=StormAttributeParser())
        storm.execute(csv)
        
        cat = self.store.get(Category, u'Despesas Operacionais')
        self.assertEqual(cat, None)
        
    def test_4_UpdateWithNoKey(self):
        '''testing Update and Delete without primary keys (uses where clause)'''
        
        csvInsertContent = '''
Category,Name
+,Contas

BudgetEntry,name,category,date,amount,scenario,payed
+,Real Mastercard,Contas,2.11.2008,6.49,plain vanilla,true
,Canto dos sonhos,Contas,4.11.2008,200.0,plain vanilla,true
+,Canto dos sonhos,Contas,4.11.2008,200.0,plain vanilla,true
'''
        
        csvUpdateContent = '''
BudgetEntry,{name},category,{date},amount,scenario,payed
~,Real Mastercard,Contas,2.11.2008,120.90,plain vanilla,false
'''
        
        csvDeleteContent = '''
model.BudgetEntry,{name},category,{date},{amount},scenario,payed
-,Canto dos sonhos,Contas,4.11.2008,200.0,plain vanilla,true
'''
        
        storm = StormORM(store=self.store)
        
        storm.execute(csvInsertContent, module=model)
        
        entry = self.store.find(BudgetEntry, BudgetEntry.name == u'Real Mastercard').one()
        self.assertEqual(entry.amount, 6.49)
        self.assertEqual(entry.payed, True)
        
        storm.execute(csvUpdateContent, modName='model')
        
        entry = self.store.find(BudgetEntry, BudgetEntry.name == u'Real Mastercard').one()
        self.assertEqual(entry.amount, 120.90)
        self.assertEqual(entry.payed, False)

        storm.execute(csvDeleteContent)
        
        c = self.store.find(BudgetEntry, BudgetEntry.name == u'Canto dos sonhos').count()
        self.assertEqual(c, 0)


class TestCSV(TestCase):
    csvContent = '''
model.Category,Name
+                   ,Casa

model.Category,Name, Parent
+                   ,Contas, Casa
+                   ,Despesas Operacionais, Casa
'''.split('\n')
    
    def test_CSV(self):
        """testing CSV"""
        csv = CSV(self.csvContent)
        self.assertEqual(len(csv.types), 2)
        self.assertEqual(len(csv.types[0].statements), 1)
        self.assertEqual(len(csv.types[1].statements), 2)
    
    def test_CSVType(self):
        '''testing CSVType'''
        csv = CSV(self.csvContent)
        self.assertEqual(len(csv.types[0].keys), 1)
        self.assertEqual(len(csv.types[0].attributes), 0)
        self.assertEqual(len(csv.types[1].keys), 1)
        self.assertEqual(len(csv.types[1].attributes), 1)
    


class TestAttributeParser(TestCase):

    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_AttributeParser(self):
        '''testing AttributeParser'''
        parser = AttributeParser()
        v = parser.parse('123')
        self.assertEqual(v, 123)
        v = parser.parse('01/01/2008')
        self.assertEqual(v, '01/01/2008')
        v = parser.parse("'123")
        self.assertEqual(v, '123')
        v = parser.parse("1.1")
        self.assertEqual(v, 1.1)
        v = parser.parse("TRUE")
        self.assertEqual(v, True)
        v = parser.parse("FALSE")
        self.assertEqual(v, False)
        v = parser.parse("wilson")
        self.assertEqual(v, 'wilson')
        
        
    def test_StormAttributeParser(self):
        '''testing StormAttributeParser'''
        parser = StormAttributeParser()
        v = parser.parse('123')
        self.assertEqual(v, 123)
        v = parser.parse('01/01/2008')
        self.assertEqual(v, date(2008, 1, 1))
        v = parser.parse("'123")
        self.assertEqual(v, u'123')
        v = parser.parse("1.1")
        self.assertEqual(v, 1.1)
        v = parser.parse("TRUE")
        self.assertEqual(v, True)
        v = parser.parse("FALSE")
        self.assertEqual(v, False)
        v = parser.parse("wilson")
        self.assertEqual(v, u'wilson')
        
        
        
if __name__ == '__main__':
    suite = TestSuite()
    suite.addTest(makeSuite(TestAttributeParser))
    suite.addTest(makeSuite(TestCSV))
    suite.addTest(makeSuite(TestStormORM))
    runner = TextTestRunner(verbosity=2)
    runner.run(suite)
