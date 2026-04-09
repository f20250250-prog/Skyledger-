                       

"""
aviation_erp/models/fuel_index_service.py
Sprint 2 – Live Fuel Indexer
Simulates an external Jet A-1 price API. In production this would call
e.g. IATA's Jet Fuel Price Monitor or a broker REST endpoint.
Result is cached in ir.config_parameter to avoid thrashing.
"""

import logging

import random

from datetime import datetime, timedelta

from odoo import api, fields, models, _



_logger = logging.getLogger(__name__)



                                                                                

_BASE_JET_A1_PRICE = 2.85                      





class FuelIndexService(models.TransientModel):

    """
    Transient model used as a service layer.
    Call `get_current_jet_a1_price()` from the Pricing Engine.
    """

    _name = 'aviation.fuel.index'

    _description = 'Jet A-1 Fuel Index Service'



                          

    CACHE_TTL_MINUTES = 30



    @api.model

    def get_current_jet_a1_price(self) -> float:

        """
        Returns the current Jet A-1 price in USD/gallon.
        Checks a 30-minute cache first; on miss, fetches (simulated) live data.
        """

        ICP = self.env['ir.config_parameter'].sudo()

        cached_price = ICP.get_param('aviation_erp.jet_a1_price_usd')

        cached_ts = ICP.get_param('aviation_erp.jet_a1_price_timestamp')



        now = datetime.utcnow()



        if cached_price and cached_ts:

            last_fetch = datetime.fromisoformat(cached_ts)

            if (now - last_fetch) < timedelta(minutes=self.CACHE_TTL_MINUTES):

                _logger.debug('Fuel index cache hit: $%.4f/gal', float(cached_price))

                return float(cached_price)



                                                                                

        price = self._fetch_jet_a1_from_api()



                        

        ICP.set_param('aviation_erp.jet_a1_price_usd', str(price))

        ICP.set_param('aviation_erp.jet_a1_price_timestamp', now.isoformat())



        _logger.info('Fuel index refreshed: $%.4f/gal (simulated)', price)

        return price



    @api.model

    def _fetch_jet_a1_from_api(self) -> float:

        """
        Simulates an HTTP call to an external fuel price API.
        Replace this block with a real `requests.get(...)` in production.

        Real endpoint example:
            url = 'https://api.iata.org/jet-fuel/price'
            resp = requests.get(url, headers={'X-API-Key': api_key}, timeout=5)
            return resp.json()['price_usd_per_gallon']
        """

                                                                               

        icp = self.env['ir.config_parameter'].sudo()

        last_price_str = icp.get_param('aviation_erp.jet_a1_price_usd')

        last_price = float(last_price_str) if last_price_str else _BASE_JET_A1_PRICE



                                    

        change_pct = random.gauss(0, 0.015)

        new_price = max(1.50, min(6.00, last_price * (1 + change_pct)))

        return round(new_price, 4)



    @api.model

    def get_fuel_surcharge_amount(self, fuel_burn_gallons: float) -> float:

        """
        Compute the raw fuel surcharge in USD for a given burn.
        """

        price_per_gallon = self.get_current_jet_a1_price()

        return round(price_per_gallon * fuel_burn_gallons, 2)

