from datetime import datetime,timedelta
from .scheduler import schedule_order
from .parser import parse_order

def test_combined_order_staggers_stations_and_hits_two_minute_window():
 now=datetime(2026,1,1);p=schedule_order([{'station':'steamer','duration_minutes':10,'quantity':1},{'station':'wok','duration_minutes':3,'quantity':1}],now)
 assert p['tasks'][0]['planned_start']==now and p['tasks'][1]['planned_start']==now+timedelta(minutes=7)
 assert p['tasks'][0]['planned_finish']==p['tasks'][1]['planned_finish']==now+timedelta(minutes=10)
 assert p['sync_success'] and p['sync_deviation_minutes']==0
def test_station_workload_affects_plan_and_infeasible_finish_is_reported():
 now=datetime(2026,1,1);p=schedule_order([{'station':'steamer','duration_minutes':10},{'station':'wok','duration_minutes':3}],now,{'steamer':now+timedelta(minutes=4),'wok':now})
 assert p['tasks'][0]['planned_start']>=now+timedelta(minutes=4)
 assert p['tasks'][1]['planned_start']>=now
 assert p['sync_success']
 infeasible=schedule_order([{'station':'steamer','duration_minutes':10},{'station':'steamer','duration_minutes':10},{'station':'wok','duration_minutes':3}],now)
 assert not infeasible['sync_success'] and infeasible['sync_deviation_minutes']>2
def test_same_station_items_are_queued_serially():
 now=datetime(2026,1,1);p=schedule_order([{'station':'steamer','duration_minutes':10},{'station':'steamer','duration_minutes':10}],now)
 assert p['tasks'][1]['planned_start']>=p['tasks'][0]['planned_finish']
def test_order_parser_example_and_invalid_items():
 p=parse_order('2 veg momo 1 chicken hakka noodles fast');assert p['valid'] and p['items'][0]['quantity']==2 and p['items'][1]['station']=='wok'
 assert not parse_order('dragon dumplings')['valid']
