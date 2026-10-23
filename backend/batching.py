from datetime import datetime,timedelta
from uuid import uuid4
from .database import connect
def optimize_batches(window_minutes:int=3):
 now=datetime.now();created=[]
 with connect() as db:
  rows=db.execute("SELECT oi.*,o.created_at FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE oi.batch_id IS NULL AND o.status IN ('queued','scheduled') AND o.created_at>=? ORDER BY oi.menu_item_id,o.created_at",((now-timedelta(minutes=window_minutes)).isoformat(),)).fetchall();groups={}
  for r in rows:groups.setdefault(r['menu_item_id'],[]).append(r)
  for mid,items in groups.items():
   by_order={};first_time=datetime.fromisoformat(items[0]['created_at'])
   for r in items:
    if datetime.fromisoformat(r['created_at'])-first_time<=timedelta(minutes=window_minutes):by_order[r['order_id']]=r
   selected=list(by_order.values())
   if len(selected)<2:continue
   bid='B-'+uuid4().hex[:6].upper();start=now;finish=start+timedelta(minutes=selected[0]['duration_minutes']);dish=selected[0]['name'];station=selected[0]['station'];db.execute('INSERT INTO batches VALUES(?,?,?,?,?,?,?,?)',(bid,mid,dish,station,now.isoformat(),start.isoformat(),finish.isoformat(),'queued'));summary=' + '.join(f"{r['quantity']} × {dish} ({r['order_id']})" for r in selected);db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',(bid,selected[0]['order_id'],station,'queued',start.isoformat(),finish.isoformat(),None,None,bid,summary))
   for r in selected:db.execute('UPDATE order_items SET batch_id=? WHERE id=?',(bid,r['id']))
   created.append({'batch_id':bid,'dish_name':dish,'orders':[{'order_id':r['order_id'],'quantity':r['quantity']} for r in selected],'total_quantity':sum(r['quantity'] for r in selected),'planned_start':start.isoformat(),'planned_finish':finish.isoformat()})
 return created
