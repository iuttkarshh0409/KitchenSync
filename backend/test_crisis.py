from decimal import Decimal
import sqlite3
import pytest
from fastapi import HTTPException
import backend.database as database
import backend.main as main
from backend.database import MENU

def cost_db(monkeypatch):
 db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;db.execute('CREATE TABLE app_config(key TEXT PRIMARY KEY,value TEXT)');db.execute('CREATE TABLE order_items(menu_item_id TEXT,ingredient_cost_per_unit REAL)')
 for m in MENU:db.execute('INSERT INTO app_config VALUES(?,?)',(f"menu_price:{m['id']}",str(m['price'])));db.execute('INSERT INTO app_config VALUES(?,?)',(f"ingredient_cost:{m['id']}",str(m.get('ingredient_cost_per_unit') or '')))
 return db

def test_client_supplied_price_cannot_override_server_menu_price():
 db=cost_db(None);row=main.normalize_items([{'menu_item_id':'veg-momo','quantity':1,'price':1,'total':0}],db)[0];assert row['price']==Decimal('129.00')
def test_menu_price_floor_and_discount_are_server_enforced():
 db=cost_db(None);db.execute("UPDATE app_config SET value='68.99' WHERE key='menu_price:veg-momo'")
 with pytest.raises(HTTPException):main.normalize_items([{'menu_item_id':'veg-momo','quantity':1}],db)
 db=cost_db(None);db.execute("UPDATE app_config SET value='69.50' WHERE key='menu_price:veg-momo'")
 with pytest.raises(HTTPException):main.normalize_items([{'menu_item_id':'veg-momo','quantity':1,'discount':'1.00'}],db)
def test_student_combo_resolves_both_brands_and_server_schedule():
 db=cost_db(None);items=main.normalize_items([{'menu_item_id':'veg-momo','quantity':1},{'menu_item_id':'hakka-noodles','quantity':1}],db);assert {x['brand'] for x in items}=={'Momobuzz','Woksum'}
 from datetime import datetime
 plan=main.schedule_order(items,datetime(2026,1,1));assert plan['sync_success'] and (plan['tasks'][1]['planned_start']-plan['tasks'][0]['planned_start']).total_seconds()==420

def test_branch_seed_is_compatible_and_keeps_jabalpur_for_review(tmp_path,monkeypatch):
 monkeypatch.setattr(database,'DB_PATH',tmp_path/'migration.sqlite');database.init_db()
 with database.connect() as db:
  rows=db.execute('SELECT * FROM branches').fetchall();assert len(rows)==2;assert all(r['is_open']==1 for r in rows)
  j=next(r for r in rows if r['id']=='jabalpur');assert j['review_status']=='Review / Consolidation Decision Required'
  assert {m['brand'] for m in MENU}=={'Momobuzz','Woksum'}
  assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==5
def test_order_submission_recalculates_server_totals_and_branch_metrics(tmp_path,monkeypatch):
 monkeypatch.setattr(database,'DB_PATH',tmp_path/'api.sqlite');database.init_db()
 result=main.create_order(main.OrderInput(items=[{'menu_item_id':'veg-momo','quantity':1,'price':'1.00','subtotal':'1.00'},{'menu_item_id':'hakka-noodles','quantity':1,'price':'1.00'}],branch_id='bhanwarkuan'))
 assert result['profitability']['item_revenue']=='348.00'
 assert result['profitability']['status']=='approved'
 assert result['tasks'][0]['planned_start']<result['tasks'][1]['planned_start']
 report=main.branches();assert len(report['branches'])==2
 j=next(b for b in report['branches'] if b['id']=='jabalpur');bh=next(b for b in report['branches'] if b['id']=='bhanwarkuan')
 assert j['decision_required'] and j['review_status']=='Review / Consolidation Decision Required' and j['is_open']
 assert bh['is_open'] and bh['order_volume']>=1 and Decimal(bh['average_ticket_size'])>0

