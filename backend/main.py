from datetime import datetime,timedelta
from decimal import Decimal
from uuid import uuid4
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from .database import MENU,connect,init_db
from .scheduler import schedule_order
from .profitability import calculate_profitability,MOMO_PRICE_FLOOR,money
from .parser import parse_order
from .batching import optimize_batches
from .analytics import summary
app=FastAPI(title='KitchenSync API',version='1.1.0');app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
def startup():init_db()
class OrderInput(BaseModel):
 items:list[dict]=Field(min_length=1);source_text:str|None=None;priority_note:str|None=None;branch_id:str='bhanwarkuan';delivery_cost:Decimal|None=None;other_cost:Decimal|None=None
class BatchInput(BaseModel):window_minutes:int=Field(default=3,ge=1,le=15)
class ConfigInput(BaseModel):platform_commission_percent:Decimal=Field(ge=0,le=100);delivery_cost:Decimal=Field(ge=0);other_order_cost:Decimal=Field(default=Decimal('0'),ge=0);minimum_contribution_profit:Decimal|None=Field(default=None,ge=0);minimum_contribution_margin_percent:Decimal|None=Field(default=None,ge=0,le=100)
class CostInput(BaseModel):menu_item_id:str;price:Decimal=Field(gt=0);ingredient_cost_per_unit:Decimal|None=Field(default=None,ge=0)
class BranchStatusInput(BaseModel):review_status:str

def dictrow(r):return {k:r[k] for k in r.keys()}
def get_config(db):return {r['key']:r['value'] for r in db.execute('SELECT * FROM app_config')}
def cast_config(config):
 return {k:(Decimal(v) if v not in (None,'') else None) for k,v in config.items()}
def availability(db):
 now=datetime.now();result={}
 for station in ('steamer','wok'):
  tasks=db.execute("SELECT planned_start,planned_finish,status FROM tasks WHERE station=? AND status IN ('queued','active') ORDER BY planned_start",(station,)).fetchall();free=now
  for t in tasks:
   start=datetime.fromisoformat(t['planned_start']);finish=datetime.fromisoformat(t['planned_finish'])
   if start>free:break
   free=max(free,finish)
  result[station]=free
 return result
def normalize_items(items,db):
 menu={x['id']:x for x in MENU};out=[]
 for it in items:
  mid=it.get('menu_item_id') or it.get('id');m=menu.get(mid)
  if not m:raise HTTPException(422,f'Unknown menu item: {mid}')
  qty=it.get('quantity',1)
  try:qty=int(qty)
  except (TypeError,ValueError):raise HTTPException(422,'Quantity must be a whole number')
  if not 1<=qty<=50:raise HTTPException(422,'Quantity must be between 1 and 50')
  cfg=get_config(db);price=money(cfg.get(f'menu_price:{mid}',m['price']));raw_cost=cfg.get(f'ingredient_cost:{mid}',m.get('ingredient_cost_per_unit'));ingredient=None if raw_cost in (None,'') else money(raw_cost)
  discount=money(it.get('discount',0))
  if discount>0:raise HTTPException(422,'Discounts are not configured. Remove the discount; momo prices must remain at least ₹69 per unit.')
  if discount<0 or discount>=price*qty:raise HTTPException(422,f'Invalid discount for {m["name"]}')
  unit_effective=(price*qty-discount)/qty
  if m['brand']=='Momobuzz' and unit_effective<MOMO_PRICE_FLOOR:raise HTTPException(422,f'{m["name"]} cannot be sold below ₹69 per unit (effective price ₹{unit_effective:.2f}). Remove the discount or change quantity/item.')
  out.append({**m,'price':price,'quantity':qty,'discount':discount,'ingredient_cost_per_unit':ingredient})
 return out
def profit_config(db):
 c=get_config(db);return {'platform_commission_percent':c.get('platform_commission_percent'),'delivery_cost':c.get('delivery_cost'),'other_order_cost':c.get('other_order_cost'),'minimum_contribution_profit':c.get('minimum_contribution_profit'),'minimum_contribution_margin_percent':c.get('minimum_contribution_margin_percent')}
@app.get('/api/health')
def health():return {'ok':True}
@app.get('/api/menu')
def menu():
 with connect() as db:
  cfg=get_config(db);items=[]
  for item in MENU:
   raw_cost=cfg.get(f"ingredient_cost:{item['id']}",item.get('ingredient_cost_per_unit'))
   items.append({**item,'price':str(money(cfg.get(f"menu_price:{item['id']}",item['price']))),'ingredient_cost_per_unit':None if raw_cost in (None,'') else str(money(raw_cost)),'momo_price_floor':'69.00' if item['brand']=='Momobuzz' else None})
  return {'items':items,'brands':[{'name':'Momobuzz','tagline':'Little folds. Big joy.','accent':'#dc623e'},{'name':'Woksum','tagline':'Fire meets flavour.','accent':'#55775e'}]}
@app.get('/api/config')
def read_config():
 with connect() as db:return cast_config(get_config(db))
@app.put('/api/config')
def write_config(data:ConfigInput):
 with connect() as db:
  for key,value in data.model_dump().items():db.execute('INSERT INTO app_config(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,None if value is None else str(value)))
  return cast_config(get_config(db))
@app.put('/api/menu/cost')
def menu_cost(data:CostInput):
 menu_item=next((x for x in MENU if x['id']==data.menu_item_id),None)
 if not menu_item:raise HTTPException(404,'Menu item not found')
 if menu_item['brand']=='Momobuzz' and data.price<MOMO_PRICE_FLOOR:raise HTTPException(422,'Momobuzz menu price cannot be below ₹69 per unit.')
 with connect() as db:
  db.execute('INSERT INTO app_config(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(f'menu_price:{data.menu_item_id}',str(data.price)))
  db.execute('INSERT INTO app_config(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(f'ingredient_cost:{data.menu_item_id}',None if data.ingredient_cost_per_unit is None else str(data.ingredient_cost_per_unit)))
  db.execute('UPDATE order_items SET ingredient_cost_per_unit=? WHERE menu_item_id=?',(None if data.ingredient_cost_per_unit is None else float(data.ingredient_cost_per_unit),data.menu_item_id));return {'menu_item_id':data.menu_item_id,'price':str(data.price),'ingredient_cost_per_unit':None if data.ingredient_cost_per_unit is None else str(data.ingredient_cost_per_unit)}
@app.get('/api/stations')
def stations():
 with connect() as db:
  now=datetime.now();out=[]
  for name in ('steamer','wok'):
   tasks=[dictrow(r) for r in db.execute("SELECT * FROM tasks WHERE station=? AND status IN ('queued','active') ORDER BY planned_start",(name,)).fetchall()];late=sum(max(0,(datetime.fromisoformat(t['planned_finish'])-now).total_seconds()/60) for t in tasks);out.append({'id':name,'name':'Steamer Station' if name=='steamer' else 'Wok Station','status':'overloaded' if late>30 else ('busy' if tasks else 'ready'),'queued_tasks':[t for t in tasks if t['status']=='queued'],'active_tasks':[t for t in tasks if t['status']=='active']})
  return out
@app.get('/api/orders')
def orders():
 with connect() as db:
  out=[]
  for r in db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall():
   x=dictrow(r);x['items']=[dictrow(i) for i in db.execute('SELECT * FROM order_items WHERE order_id=?',(r['id'],)).fetchall()];x['tasks']=[dictrow(t) for t in db.execute('SELECT * FROM tasks WHERE order_id=?',(r['id'],)).fetchall()];out.append(x)
  return out
@app.post('/api/orders')
def create_order(data:OrderInput):
 with connect() as db:
  branch=db.execute('SELECT * FROM branches WHERE id=?',(data.branch_id,)).fetchone()
  if not branch or not branch['is_open']:raise HTTPException(422,'Selected branch is not open for orders.')
  items=normalize_items(data.items,db);result=calculate_profitability(items,profit_config(db),data.delivery_cost if data.delivery_cost is not None else 0,data.other_cost if data.other_cost is not None else Decimal(profit_config(db).get('other_order_cost') or 0))
  if result['status']!='approved':raise HTTPException(422,{'message':'Combo needs adjustment before submission.','profitability':result})
  now=datetime.now();plan=schedule_order(items,now,availability(db));oid='KS-'+uuid4().hex[:6].upper();db.execute('INSERT INTO orders(id,created_at,status,priority_note,source_text,estimated_minutes,sync_deviation,sync_success,branch_id,item_revenue,estimated_cost,contribution_profit) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(oid,now.isoformat(),'queued',data.priority_note,data.source_text,plan['estimated_minutes'],plan['sync_deviation_minutes'],int(plan['sync_success']),data.branch_id,result['item_revenue'],result['total_estimated_cost'],result['contribution_profit']))
  for n,t in enumerate(plan['tasks']):
   iid=f'{oid}-I{n+1}';tid=f'{oid}-T{n+1}';cost=t.get('ingredient_cost_per_unit');db.execute('INSERT INTO order_items(id,order_id,menu_item_id,name,brand,station,quantity,unit_price,duration_minutes,ingredient_cost_per_unit) VALUES(?,?,?,?,?,?,?,?,?,?)',(iid,oid,t['id'],t['name'],t['brand'],t['station'],t['quantity'],str(t['price']),t['duration_minutes'],None if cost is None else str(cost)));db.execute('INSERT INTO tasks(id,order_id,station,status,planned_start,planned_finish,item_summary) VALUES(?,?,?,?,?,?,?)',(tid,oid,t['station'],'queued',t['planned_start'].isoformat(),t['planned_finish'].isoformat(),f"{t['quantity']} × {t['name']}"))
  return {'order_id':oid,'status':'queued','estimated_minutes':round(plan['estimated_minutes'],1),'sync_deviation_minutes':plan['sync_deviation_minutes'],'sync_success':plan['sync_success'],'target_window_minutes':2,'tasks':[{'dish_name':t['name'],'station':t['station'],'duration_minutes':t['duration_minutes'],'planned_start':t['planned_start'].isoformat(),'planned_finish':t['planned_finish'].isoformat()} for t in plan['tasks']],'profitability':result}
@app.post('/api/orders/preview')
def preview(data:OrderInput):
 with connect() as db:
  items=normalize_items(data.items,db);profit=calculate_profitability(items,profit_config(db),data.delivery_cost if data.delivery_cost is not None else 0,data.other_cost if data.other_cost is not None else Decimal(profit_config(db).get('other_order_cost') or 0));plan=schedule_order(items,datetime.now(),availability(db));return {'profitability':profit,'schedule':{'estimated_minutes':plan['estimated_minutes'],'sync_deviation_minutes':plan['sync_deviation_minutes'],'sync_success':plan['sync_success'],'target_window_minutes':2,'tasks':[{'dish_name':t['name'],'brand':t['brand'],'station':t['station'],'duration_minutes':t['duration_minutes'],'planned_start':t['planned_start'].isoformat(),'planned_finish':t['planned_finish'].isoformat()} for t in plan['tasks']]}}
@app.get('/api/orders/{order_id}')
def order_detail(order_id:str):
 with connect() as db:
  r=db.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
  if not r:raise HTTPException(404,'Order not found')
  return {**dictrow(r),'items':[dictrow(x) for x in db.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,)).fetchall()],'tasks':[dictrow(x) for x in db.execute('SELECT * FROM tasks WHERE order_id=?',(order_id,)).fetchall()]}
@app.post('/api/orders/{order_id}/schedule')
def reschedule(order_id:str):
 with connect() as db:
  r=db.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
  if not r:raise HTTPException(404,'Order not found')
  items=[dictrow(x) for x in db.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,)).fetchall()];plan=schedule_order(items,datetime.fromisoformat(r['created_at']),availability(db));return {'estimated_minutes':plan['estimated_minutes'],'sync_deviation_minutes':plan['sync_deviation_minutes'],'sync_success':plan['sync_success'],'tasks':[{'station':t['station'],'planned_start':t['planned_start'].isoformat(),'planned_finish':t['planned_finish'].isoformat()} for t in plan['tasks']]}
def transition(task_id,action):
 with connect() as db:
  t=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
  if not t:raise HTTPException(404,'Task not found')
  now=datetime.now().isoformat()
  if action=='start' and t['status']!='queued':raise HTTPException(409,f"Cannot start task in {t['status']} state")
  if action=='complete' and t['status']!='active':raise HTTPException(409,f"Cannot complete task in {t['status']} state")
  if action=='start':db.execute("UPDATE tasks SET status='active',actual_start=? WHERE id=?",(now,task_id))
  else:
   db.execute("UPDATE tasks SET status='completed',actual_finish=? WHERE id=?",(now,task_id));linked=[t['order_id']]
   if t['batch_id']:linked=[x['order_id'] for x in db.execute('SELECT order_id FROM order_items WHERE batch_id=?',(t['batch_id'],)).fetchall()]
   for oid in set(linked):
    if db.execute("SELECT COUNT(*) n FROM tasks WHERE order_id=? AND status!='completed'",(oid,)).fetchone()['n']==0:db.execute("UPDATE orders SET status='completed',completed_at=? WHERE id=?",(now,oid))
  return {'task_id':task_id,'status':'active' if action=='start' else 'completed'}
@app.post('/api/tasks/{task_id}/start')
def start(task_id:str):return transition(task_id,'start')
@app.post('/api/tasks/{task_id}/complete')
def complete(task_id:str):return transition(task_id,'complete')
@app.post('/api/orders/parse')
def parse(data:dict):return parse_order(str(data.get('text','')))
@app.get('/api/batches')
def batches():
 with connect() as db:return [dictrow(x) for x in db.execute('SELECT * FROM batches ORDER BY created_at DESC').fetchall()]
@app.post('/api/batches/optimize')
def batches_optimize(data:BatchInput):return {'batches':optimize_batches(data.window_minutes)}
@app.get('/api/analytics/summary')
def analytics(from_date:str|None=None,to_date:str|None=None):return summary(from_date,to_date)
@app.post('/api/estimates')
def estimates(data:OrderInput):
 with connect() as db:
  items=normalize_items(data.items,db);p=schedule_order(items,datetime.now(),availability(db));return {'estimated_minutes':round(p['estimated_minutes'],1),'sync_success':p['sync_success'],'sync_deviation_minutes':p['sync_deviation_minutes'],'tasks':[{'station':t['station'],'duration_minutes':t['duration_minutes'],'planned_start':t['planned_start'].isoformat(),'planned_finish':t['planned_finish'].isoformat()} for t in p['tasks']]}
@app.get('/api/branches')
def branches(from_date:str|None=None,to_date:str|None=None):
 with connect() as db:
  result=[]
  for b in db.execute('SELECT * FROM branches ORDER BY name').fetchall():
   clauses=['branch_id=?'];args=[b['id']]
   if from_date:clauses.append('date(created_at)>=date(?)');args.append(from_date)
   if to_date:clauses.append('date(created_at)<=date(?)');args.append(to_date)
   rows=db.execute('SELECT * FROM orders WHERE '+' AND '.join(clauses),args).fetchall();revenue=Decimal('0.00')
   for order in rows:
    if order['item_revenue'] is not None:revenue+=Decimal(str(order['item_revenue']))
    else:
     for item in db.execute('SELECT quantity,unit_price FROM order_items WHERE order_id=?',(order['id'],)).fetchall():revenue+=Decimal(str(item['unit_price']))*int(item['quantity'])
   durations=[(datetime.fromisoformat(r['completed_at'])-datetime.fromisoformat(r['created_at'])).total_seconds()/60 for r in rows if r['completed_at']];success=sum(bool(r['sync_success']) for r in rows if r['completed_at']);cap=b['capacity_per_day'];count=len(rows);synthetic=sum(r['id'].startswith('DEMO-') for r in rows);result.append({'id':b['id'],'name':b['name'],'city':b['city'],'order_volume':count,'synthetic_orders':synthetic,'average_ticket_size':str((revenue/count).quantize(Decimal('.01')) if count else Decimal('0')),'revenue':str(revenue.quantize(Decimal('.01'))),'capacity_per_day':cap,'capacity_utilization_percent':round(count*100/cap,1) if cap else 0,'average_preparation_minutes':round(sum(durations)/len(durations),1) if durations else None,'sync_success_rate':round(success*100/sum(bool(r['completed_at']) for r in rows),1) if any(r['completed_at'] for r in rows) else None,'is_open':bool(b['is_open']),'review_status':b['review_status'],'decision_required':b['id']=='jabalpur'})
  return {'branches':result,'scenario_inputs':{'walk_in_orders_change_percent':-45,'ticket_before':180,'ticket_current':125,'competitor_momo_price':59},'data_note':'Metrics include synthetic DEMO orders where labeled. Branch capacities are configured demo values; crisis figures are organiser scenario inputs.'}
@app.put('/api/branches/{branch_id}/review')
def set_branch_review(branch_id:str,data:BranchStatusInput):
 allowed={'Open','Under review','Review / Consolidation Decision Required'}
 if data.review_status not in allowed:raise HTTPException(422,'Unsupported review status')
 with connect() as db:
  b=db.execute('SELECT * FROM branches WHERE id=?',(branch_id,)).fetchone()
  if not b:raise HTTPException(404,'Branch not found')
  db.execute('UPDATE branches SET review_status=? WHERE id=?',(data.review_status,branch_id));return {'id':branch_id,'review_status':data.review_status,'is_open':bool(b['is_open']),'message':'Review status updated; branch operation status is unchanged.'}

