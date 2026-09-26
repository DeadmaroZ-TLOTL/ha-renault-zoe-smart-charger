"""Regression coverage for shared operator accounts and vehicle locations."""
import importlib.util
import ast
from pathlib import Path
import sys
import types
import unittest

root=Path(__file__).parents[1]/'custom_components/zoe_new_extended'
package=types.ModuleType('_location_test_pkg'); package.__path__=[str(root)]
sys.modules[package.__name__]=package
spec=importlib.util.spec_from_file_location('_location_test_pkg.charging_location_data',root/'charging_location_data.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class LocationTests(unittest.TestCase):
    def test_pyscript_has_no_unsupported_generator_expressions(self):
        source=Path(__file__).parents[1]/'smart_charger/pyscript/zoe_charge_sessions.py'
        self.assertFalse(any(isinstance(n,ast.GeneratorExp) for n in ast.walk(ast.parse(source.read_text(encoding='utf-8')))))

    def setUp(self):
        self.tx={'account_id':'a','transaction_id':'1611362','source_account_type':'ignitis_on',
                 'station_id':'622','start':'2026-09-18T13:42:28+00:00','end':'2026-09-18T14:15:14+00:00',
                 'energy_kwh':11.977,'total_cost_eur':4.19,'provider_reported_cost':True,'price_source':'ignitis_on_app'}
        self.station={'provider':'ignitis_on','id':'622','latitude':56.95,'longitude':24.2}
        self.points=[{'time':'2026-09-18T13:45:00+00:00','latitude':56.95,'longitude':24.2},
                     {'time':'2026-09-18T14:10:00+00:00','latitude':56.95,'longitude':24.2}]

    def check(self,points=None,stations=None):
        return module.check_transaction_locations([self.tx],self.points if points is None else points,
                                                   [self.station] if stations is None else stations)

    def test_confirmed_station_allows_missing_renault_row(self):
        verified=self.check()
        self.assertIs(verified[0]['vehicle_location_match'],True)
        rows=module.apply_location_verified_transactions([],verified)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['total_cost_eur'],4.19)

    def test_shared_account_charge_elsewhere_excluded(self):
        points=[dict(p,longitude=25) for p in self.points]
        verified=self.check(points)
        self.assertIs(verified[0]['vehicle_location_match'],False)
        self.assertEqual(module.apply_location_verified_transactions([],verified),[])
        self.assertNotIn('vehicle_location_match',self.tx)

    def test_same_time_renault_charge_does_not_override_location(self):
        verified=self.check([dict(p,longitude=25) for p in self.points])
        session={'start':self.tx['start'],'end':self.tx['end'],'start_soc':20,'end_soc':40}
        rows=module.apply_location_verified_transactions([session],verified)
        self.assertEqual(len(rows),1)
        self.assertNotIn('provider_transaction_id',rows[0])

    def test_missing_gps_is_not_vehicle_evidence(self):
        self.assertEqual(module.apply_location_verified_transactions([],self.check([])),[])

    def test_current_or_old_position_is_not_historical_evidence(self):
        for stamp in ('2026-09-26T13:45:00+00:00','2026-09-18T13:40:00+00:00'):
            verified=self.check([dict(p,time=stamp) for p in self.points])
            self.assertIsNone(verified[0]['vehicle_location_match'])

    def test_provider_ids_do_not_collide(self):
        self.assertIsNone(self.check(stations=[dict(self.station,provider='mobilly')])[0]['vehicle_location_match'])

    def test_conflicting_or_inaccurate_gps_unknown(self):
        self.assertIsNone(self.check([self.points[0],dict(self.points[1],longitude=25)])[0]['vehicle_location_match'])
        self.assertIsNone(self.check([dict(p,gps_accuracy=500) for p in self.points])[0]['vehicle_location_match'])

    def test_single_fix_and_invalid_coordinates_unknown(self):
        self.assertIsNone(self.check(self.points[:1])[0]['vehicle_location_match'])
        self.assertIsNone(self.check([dict(p,latitude=float('nan')) for p in self.points])[0]['vehicle_location_match'])

    def test_unknown_location_with_renault_record_keeps_exact_cost(self):
        session={'start':self.tx['start'],'end':self.tx['end'],'start_soc':20,'end_soc':40}
        rows=module.apply_location_verified_transactions([session],self.check([]))
        self.assertEqual(rows[0]['total_cost_eur'],4.19)


if __name__=='__main__':
    unittest.main()
