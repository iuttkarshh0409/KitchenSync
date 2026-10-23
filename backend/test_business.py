from decimal import Decimal
from backend.profitability import calculate_profitability,MOMO_PRICE_FLOOR
from backend.database import init_db,connect

def setup_function():init_db()
def test_momo_floor_exactly_69_and_below():
 assert Decimal('69.00')>=MOMO_PRICE_FLOOR
 item={'id':'m','name':'Veg Momo','brand':'Momobuzz','price':69,'quantity':1,'ingredient_cost_per_unit':30}
 c={'platform_commission_percent':0,'delivery_cost':0};assert calculate_profitability([item],c,delivery_cost=1)['status']=='approved'
 item['price']=Decimal('68.99');assert any('below ₹69' in x for x in calculate_profitability([item],c,delivery_cost=1)['violations'])
def test_discount_cannot_cross_momo_floor():
 item={'id':'m','name':'Veg Momo','brand':'Momobuzz','price':70,'quantity':1,'discount':2,'ingredient_cost_per_unit':30};r=calculate_profitability([item],{'platform_commission_percent':0,'delivery_cost':1});assert any('below ₹69' in x for x in r['violations'])
def test_profitability_approval_block_and_missing_cost_warning():
 momo={'id':'m','name':'Veg Momo','brand':'Momobuzz','price':129,'quantity':1,'ingredient_cost_per_unit':30};wok={'id':'w','name':'Noodles','brand':'Woksum','price':219,'quantity':1,'ingredient_cost_per_unit':70};good=calculate_profitability([momo,wok],{'platform_commission_percent':10,'delivery_cost':20,'minimum_contribution_margin_percent':20});assert good['status']=='approved' and Decimal(good['contribution_profit'])==Decimal('193.20')
 bad=calculate_profitability([momo,wok],{'platform_commission_percent':50,'delivery_cost':500,'minimum_contribution_margin_percent':20});assert bad['status']=='blocked'
 missing=calculate_profitability([{**momo,'ingredient_cost_per_unit':None}],{'platform_commission_percent':10,'delivery_cost':20});assert missing['status']=='incomplete_costs' and missing['warnings'] and missing['contribution_profit'] is None and missing['contribution_margin_percent'] is None
def test_branch_review_data_keeps_both_open():
 with connect() as db:
  branches=db.execute('SELECT * FROM branches').fetchall();assert {b['name'] for b in branches}>={'Bhanwarkuan','Jabalpur'};assert all(b['is_open'] for b in branches);assert next(b for b in branches if b['name']=='Jabalpur')['review_status']=='Review / Consolidation Decision Required'
