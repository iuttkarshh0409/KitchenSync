from datetime import datetime, timedelta
import os
from pathlib import Path
import sqlite3
DB_PATH=Path(os.environ.get('KITCHENSYNC_DB_PATH', '/tmp/kitchensync.db' if os.environ.get('VERCEL') else Path(__file__).parent/'kitchensync.db'))
MENU=[
{"id":"veg-momo","name":"Steamed Veg Momos","brand":"Momobuzz","station":"steamer","category":"Steamed momos","description":"Hand-folded cabbage, carrot and ginger dumplings","price":129,"ingredient_cost_per_unit":42,"duration_minutes":10,"aliases":["veg momo","veg momos","steamed veg momo","momos"]},
{"id":"chicken-momo","name":"Chicken Momos","brand":"Momobuzz","station":"steamer","category":"Steamed momos","description":"Juicy chicken dumplings with a house chilli dip","price":159,"ingredient_cost_per_unit":57,"duration_minutes":10,"aliases":["chicken momo","chicken momos"]},
{"id":"fried-momo","name":"Crispy Fried Momos","brand":"Momobuzz","station":"steamer","category":"Fried momos","description":"Crisp pan-fried dumplings with sesame chilli oil","price":149,"ingredient_cost_per_unit":48,"duration_minutes":8,"aliases":["fried momo","fried momos","crispy momos"]},
{"id":"hakka-noodles","name":"Chicken Hakka Noodles","brand":"Woksum","station":"wok","category":"Wok favourites","description":"Smoky wok-tossed noodles with chicken and greens","price":219,"ingredient_cost_per_unit":86,"duration_minutes":3,"aliases":["chicken hakka noodles","hakka noodles","chicken noodles"]},
{"id":"veg-fried-rice","name":"Veg Fried Rice","brand":"Woksum","station":"wok","category":"Wok favourites","description":"Wok-fired rice with seasonal vegetables and spring onion","price":189,"ingredient_cost_per_unit":67,"duration_minutes":3,"aliases":["veg fried rice","vegetable fried rice"]},
{"id":"chilli-paneer","name":"Chilli Paneer","brand":"Woksum","station":"wok","category":"Wok favourites","description":"Paneer, peppers and onions in a lively chilli glaze","price":229,"ingredient_cost_per_unit":91,"duration_minutes":4,"aliases":["chilli paneer","chili paneer"]}]
def connect():
 db=sqlite3.connect(DB_PATH);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
def init_db():
 with connect() as db:
  db.executescript('''CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,priority_note TEXT,source_text TEXT,estimated_minutes REAL NOT NULL DEFAULT 0,sync_deviation REAL NOT NULL DEFAULT 0,sync_success INTEGER NOT NULL DEFAULT 1,completed_at TEXT);CREATE TABLE IF NOT EXISTS order_items(id TEXT PRIMARY KEY,order_id TEXT NOT NULL REFERENCES orders(id),menu_item_id TEXT NOT NULL,name TEXT NOT NULL,brand TEXT NOT NULL,station TEXT NOT NULL,quantity INTEGER NOT NULL,unit_price REAL NOT NULL,duration_minutes INTEGER NOT NULL,batch_id TEXT);CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,order_id TEXT NOT NULL REFERENCES orders(id),station TEXT NOT NULL,status TEXT NOT NULL,planned_start TEXT NOT NULL,planned_finish TEXT NOT NULL,actual_start TEXT,actual_finish TEXT,batch_id TEXT,item_summary TEXT NOT NULL);CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY,menu_item_id TEXT NOT NULL,dish_name TEXT NOT NULL,station TEXT NOT NULL,created_at TEXT NOT NULL,planned_start TEXT NOT NULL,planned_finish TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS branches(id TEXT PRIMARY KEY,name TEXT NOT NULL,city TEXT NOT NULL,capacity_per_day INTEGER NOT NULL,is_open INTEGER NOT NULL DEFAULT 1,review_status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS app_config(key TEXT PRIMARY KEY,value TEXT);''')
  ensure_column(db,'orders','branch_id','TEXT REFERENCES branches(id)')
  db.executemany('INSERT OR IGNORE INTO branches(id,name,city,capacity_per_day,is_open,review_status) VALUES(?,?,?,?,?,?)',[('bhanwarkuan','Bhanwarkuan','Indore',80,1,'Open'),('jabalpur','Jabalpur','Jabalpur',60,1,'Review / Consolidation Decision Required')])
  defaults={'platform_commission_percent':'20','delivery_cost':'25','minimum_contribution_profit':'0','minimum_contribution_margin_percent':'0','other_order_cost':'0'}
  for key,value in defaults.items():db.execute('INSERT OR IGNORE INTO app_config(key,value) VALUES(?,?)',(key,value))
  for item in MENU:
   db.execute('INSERT OR IGNORE INTO app_config(key,value) VALUES(?,?)',(f"menu_price:{item['id']}",str(item['price'])))
   db.execute('INSERT OR IGNORE INTO app_config(key,value) VALUES(?,?)',(f"ingredient_cost:{item['id']}",str(item['ingredient_cost_per_unit'])))
  if not db.execute('SELECT 1 FROM orders LIMIT 1').fetchone(): seed_demo(db)
  ensure_column(db,'order_items','ingredient_cost_per_unit','REAL')
  ensure_column(db,'orders','item_revenue','TEXT')
  ensure_column(db,'orders','estimated_cost','TEXT')
  ensure_column(db,'orders','contribution_profit','TEXT')
  ensure_column(db,'orders','branch_id','TEXT REFERENCES branches(id)')
  for item in MENU:db.execute('UPDATE order_items SET ingredient_cost_per_unit=? WHERE menu_item_id=? AND ingredient_cost_per_unit IS NULL',(item.get('ingredient_cost_per_unit'),item['id']))
  db.execute("UPDATE orders SET branch_id='bhanwarkuan' WHERE id IN ('DEMO-101','DEMO-102','DEMO-104','DEMO-105') AND branch_id IS NULL")
  db.execute("UPDATE orders SET branch_id='jabalpur' WHERE id='DEMO-103' AND branch_id IS NULL")
def seed_demo(db):
 base=datetime.now().replace(hour=12,minute=15,second=0,microsecond=0)
 for oi,(oid,items) in enumerate([('DEMO-101',[('veg-momo',2),('hakka-noodles',1)]),('DEMO-102',[('veg-momo',1),('veg-fried-rice',1)]),('DEMO-103',[('veg-momo',2)]),('DEMO-104',[('chicken-momo',1),('chilli-paneer',1)]),('DEMO-105',[('hakka-noodles',2),('fried-momo',1)])]):
  created=base+timedelta(minutes=oi*2);branch='jabalpur' if oid=='DEMO-103' else 'bhanwarkuan';db.execute('INSERT INTO orders(id,created_at,status,priority_note,source_text,estimated_minutes,sync_deviation,sync_success,completed_at,branch_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(oid,created.isoformat(),'completed',None,None,13+oi,1,1,(created+timedelta(minutes=14+oi)).isoformat(),branch))
  for ix,(mid,q) in enumerate(items):
   m=next(x for x in MENU if x['id']==mid);db.execute('INSERT INTO order_items VALUES(?,?,?,?,?,?,?,?,?,NULL)',(f'{oid}-I{ix+1}',oid,mid,m['name'],m['brand'],m['station'],q,m['price'],m['duration_minutes']))
   start=created+timedelta(minutes=0 if m['station']=='steamer' else 7);finish=start+timedelta(minutes=m['duration_minutes'])
   db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,NULL,?)',(f'{oid}-T{ix+1}',oid,m['station'],'completed',start.isoformat(),finish.isoformat(),start.isoformat(),finish.isoformat(),f"{q} × {m['name']}"))


def ensure_column(db,table,column,definition):
 columns={r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
 if column not in columns:db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

