from helpers import *
from codes_joint import *
from datetime import datetime
from pandas import DataFrame
# from pdb import set_trace
from numpy import vectorize
import yaml

class RosterWriter(object):
    def __init__(self, roster, curr_folder):
        self.set_curr_folder(curr_folder)
        self.table = roster.get_table()
        self.roster_type = roster.get_roster_type()
        self.order_type = roster.get_order_type()
        self.LL_earnings_overrides = roster.get_LL_earnings_overrides()
        self.LL_cap_status = roster.LL_cap_status

    def set_curr_folder(self, folder):
        self.curr_folder = folder + OUTPUT_PATH

    def timestamp(self):
        return datetime.now().strftime('%m-%d-%y_%H%M')

    def save_roster(self):
        wb = load_workbook(CONFIG_PATH + 'trade roster - template.xlsx', data_only=True)
        sheet = wb['roster']
        write_column_xlsx(sheet, 'a', 3, self.table.send_to_roster)
        write_column_xlsx(sheet, 'b', 3, self.table.route)
        write_column_xlsx(sheet, 'c', 3, self.table.strategy)
        write_column_xlsx(sheet, 'd', 3, self.table.book)
        write_column_xlsx(sheet, 'e', 3, self.table.ticker)
        write_column_xlsx(sheet, 'f', 3, self.table.actual_shares)
        write_column_xlsx(sheet, 'g', 3, self.table.target_shares)
        write_column_xlsx(sheet, 'h', 3, self.table.direction_human)
        write_column_xlsx(sheet, 'i', 3, self.table.quantity)
        write_column_xlsx(sheet, 'j', 3, self.table.price, update_to_currency = True)
        write_column_xlsx(sheet, 'k', 3, self.table.limit_price)
        write_column_xlsx(sheet, 'l', 3, self.table.quantity * self.table.price, update_to_currency = True)
        write_column_xlsx(sheet, 'm', 3, self.table.NAV_diff)
        write_column_xlsx(sheet, 'n', 3, self.table.rank_long)
        write_column_xlsx(sheet, 'o', 3, self.table.rank_avg)
        write_column_xlsx(sheet, 'p', 3, self.table.rank_short)
        write_column_xlsx(sheet, 'q', 3, self.table.pct_of_20d_ATV)
        write_column_xlsx(sheet, 'r', 3, self.table['20d_ATV'])
        write_column_xlsx(sheet, 's', 3, self.table.rank_vs_15d_avg)
        write_column_xlsx(sheet, 't', 3, self.table.todays_price_return)
        write_column_xlsx(sheet, 'u', 3, self.table.reversal)
        write_column_xlsx(sheet, 'v', 3, self.table.low_liquidity)
        write_column_xlsx(sheet, 'w', 3, self.table.description)
        write_column_xlsx(sheet, 'x', 3, self.table.cons_type)
        write_column_xlsx(sheet, 'y', 3, self.table.cons_id)
        write_column_xlsx(sheet, 'z', 3, self.table.alloc_strat_1)
        write_column_xlsx(sheet, 'aa', 3, self.table.alloc_strat_2)
        write_column_xlsx(sheet, 'ab', 3, self.table.alloc_strat_3)
        write_column_xlsx(sheet, 'ac', 3, self.table.alloc_strat_1_joint)
        write_column_xlsx(sheet, 'ad', 3, self.table.alloc_strat_2_joint)
        write_column_xlsx(sheet, 'ae', 3, self.table.alloc_strat_3_joint)
        write_column_xlsx(sheet, 'af', 3, self.table.alloc_Dual)
        write_column_xlsx(sheet, 'ag', 3, self.table.send_to_sheet)

        if self.order_type == 'MOC':
            filename = (self.curr_folder + 'BDC_trade_sheet_EOD_' + self.timestamp() + '.xlsx')
        else:
            filename = (self.curr_folder + 'BDC_trade_sheet_' + self.timestamp() + '.xlsx')
        wb.save(filename)
        print()
        print('  >>  Trade sheet saved to ' + filename + '.')


    # until Phil confirms combo schema, we're using CF "GENERAL" schema for consolidated trades
    def save_csv_temporary(self):
        temp = self.table.loc[self.table.send_to_roster, :].copy()
        result = DataFrame({'schema' : temp.schema_temporary})
        result['ticker'] = temp.broker_ticker
        result['exec_strategy'] = temp.route
        result['side'] = temp.direction
        result['qty'] = temp.quantity
        if self.order_type in ['LOO', 'LMT regular', 'LMT manual', 'LMT regular 50pct']:
            result['lmt_price'] = self.table.limit_price
        filename = (self.curr_folder + 'BDC_trade_roster_GEN_' + ROSTER_CODES['csv'][self.roster_type] + '_' + self.timestamp() + '.csv')
        result.to_csv(filename, index = False, header = False)
        print('  >>  OMS roster ' + self.order_type + ' saved to ' + filename + '.')

    def save_csv_permanent(self, route_filter = 'all'):
        temp = self.table.loc[self.table.send_to_roster, :]
        if route_filter != 'all':
            temp = temp.loc[temp.route == ROUTES[route_filter], :]

        result = DataFrame({'schema' : temp.schema_permanent})
        result['ticker'] = temp.broker_ticker
        result['exec_strategy'] = temp.route
        result['side'] = temp.direction
        result['qty'] = temp.quantity
        # once Phil confirms that pipe codes work, append pipe code to limit price (and "" if none)
        if self.order_type in ['LOO', 'LMT regular', 'LMT manual', 'LMT regular 50pct']:
            result['lmt_price'] = self.table.limit_price
        temp.loc[temp.pipe_code == '-1', 'pipe_code'] = ''
        result['pipe_code'] = temp.pipe_code
        filename = (self.curr_folder + 'BDC_trade_roster_combo_' + route_filter + '_' + self.timestamp() + '.csv')
        result.to_csv(filename, index = False, header = False)
        print('  >>  OMS roster ' + self.order_type + ' saved to ' + filename + '.')

    # temporary, until combo schema is functional
    def save_allocations(self):
        temp = self.table.loc[self.table.strategy == 'consolidated', :].copy()
        if temp.shape[0] > 0:
            result = DataFrame({'ticker' : temp.broker_ticker})
            result['strategy_code'] = temp.alloc_sheet_string
            result['qty'] = temp.quantity
            result['strat_1'] = temp.alloc_strat_1
            result['strat_2'] = temp.alloc_strat_2
            result['strat_3'] = temp.alloc_strat_3
            result['strat_1_joint'] = temp.alloc_strat_1_joint
            result['strat_2_joint'] = temp.alloc_strat_2_joint
            result['strat_3_joint'] = temp.alloc_strat_3_joint
            result['Dual'] = temp.alloc_Dual
            result['strat_4'] = temp.alloc_strat_4

            filename = (self.curr_folder + 'post-trade_allocation_' + self.timestamp() + '.csv')
            result.to_csv(filename, index = False, header = True)
            print('  >>  Trade allocation saved to ' + filename + '.')

    def save_LL_list(self):
        LL = self.table.loc[self.table.low_liquidity == 1, ['strategy', 'book', 'ticker']]
        result = {}
        for strat in sorted(list(set(LL.strategy))):
            LL_subset = LL.loc[LL.strategy == strat]
            strat_section = {}
            for sector in sorted(list(set(LL_subset.book))):
                strat_section[sector] = ' '.join(sorted(list(set(LL_subset.loc[LL_subset.book == sector, 'ticker']))))
            result[strat] = strat_section
        combined_list = sorted(list(set(LL.ticker) - set(self.LL_earnings_overrides)))
        result['combined'] = ' '.join(combined_list)
        LL_yml_filename = (self.curr_folder + 'LL_leftovers_' + self.timestamp() + '.yml')
        with open(LL_yml_filename, 'w') as outfile:
            yaml.dump(result, outfile, default_flow_style = False, width = 1000)
        print('  >>  LL leftovers for tomorrow morning saved to ' + LL_yml_filename + '.')

    def execute(self):
        self.save_roster()

        if self.roster_type == 'A':
            # temporary, while we have to send strat_2 to Merrill separately and not consolidate,
            # EOD trades will create two separate csv files
            self.save_csv_permanent('MOC')
            self.save_csv_permanent('VWAP')
        else:
            self.save_csv_temporary()
            # self.save_csv_permanent()

        self.save_allocations()

        if (self.roster_type in ['A', 'E', 'F']) & (sum(self.table.low_liquidity) > 0) & (self.LL_cap_status == 'ON'):
            self.save_LL_list()
