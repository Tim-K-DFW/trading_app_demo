# from pdb import set_trace
from pandas import read_excel, read_csv
from string import ascii_lowercase
from numpy import vectorize
from codes_joint import *
import UI
import datetime

class FileReader(object):
    '''
    given source_file dictionary, returns dataframe representing that research book (one of primero ones or the jump)
    almost all output columns read in, several are computed
    hardcoded params in Excel sheet are coordinates of universe size, index of first data row and # of columns to load, DF notation used to access them
    '''
    def __init__(self, dict, curr_folder, args):
        self.filename = dict['file']
        self.sheet = dict['sheet']
        self.curr_folder = curr_folder
        self.strat = dict['strat']
        self.cols = self.read_excel_col_codes(self.strat)
        self.cells = dict['cells']
        self.first_row = self.cells['first_row']
        self.univ_size = self.cells['univ_size']
        self.cols_to_load = self.cells['cols_to_load']
        self.args = args

    def read_excel_col_codes(self, strategy):
        '''
        reads Excel column codes from csv file which needs to be in project main folder
        (this was previously part of codes.py but got too noisy and cumbersome)
        column names of csv file must match strat keys of `source_files` in `codes`
        '''
        csv = read_csv(CONFIG_PATH + 'excel_columns.csv')
        result = {csv.item[i] : csv.loc[i, strategy] for i in range(csv.shape[0])}
        return result

    def load_from_excel(self):
        print('Loading ' + self.filename + '/' + self.sheet + '... hang on...')
        fn = self.curr_folder + self.filename
        sheet = read_excel(fn, sheet_name=self.sheet, usecols=self.cols_to_load, header=None)
        if self.strat == 'strat_1' and '-nocheck' not in self.args:
            reconcile_time = sheet.iloc[1,25]
            now = datetime.datetime.now()
            max_delta = datetime.timedelta(hours = 1.5)
            if now - reconcile_time > max_delta:
                print('\n\nThat\'s interesting... The time is now ' + now.strftime("%H:%M:%S") + '...')
                print('... and last time you reconciled positions was at ' +  reconcile_time.strftime("%H:%M:%S") + '...')
                print('Didn\'t you just tell me that you have reconciled AND SAVED positions? You have actually TYPED the entire word "reconciled" to confirm that.\n\n\n\n\n')
                UI.error_exit('  >>  GTFOH.')

        univ_size = sheet.iloc[self.univ_size]
        last_row = self.first_row - 1 + univ_size
        table = sheet.copy().iloc[self.first_row - 1 : last_row, :]
        table.columns = sheet.iloc[self.first_row - 2, :]
        self.table = table
        self.table_full = table.copy()
        print('Done!')

    def rename_columns(self):
        '''
        1. changes colnames from those in Excel to those used later here
        2. removes all the other columns
        length of excel_colnames must match `cols_to_load`, otherwise it breaks
        '''
        excel_colnames = [p + i for p in ['', 'a', 'b', 'c', 'd'] for i in ascii_lowercase][0:self.cols_to_load + 1]

        # if there are any blank columns (because of mismatch in Primero vs Jump files), add dummy columns so it doesn't throw an error
        if self.table.shape[1] < len(excel_colnames):
            for i in range(1, len(excel_colnames) - self.table.shape[1] + 1):
                self.table['extra_' + str(i)] = ['--'] * self.table.shape[0]
        self.table.columns = excel_colnames

        self.table = self.table.loc[:, list(self.cols.values())]
        self.table.columns = self.cols.keys()

    def add_computed_columns(self):
        '''
        so far, we only add strategy in the script, the rest is computed in Excel
        but can add something in the future
        '''
        self.table['strategy'] = self.strat

    def one_off_adjustments(self):
        '''
        idiosyncratic stuff for strategy files that diverge from the template (e.g. SQUIRREL)
        '''
        if self.strat == 'squirrel':
            self.table.LL_capped_qty = abs(self.table.LL_capped_qty)
            cols_to_reset = ['low_liquidity', 'NAV_diff', 'rank_long', 'rank_avg', 'rank_short', 'limit_price', 'pct_of_20d_ATV', '20d_ATV']
            self.table.loc[:, cols_to_reset] = 0

    def clean_up(self):
        '''
        keeps only rows where direction is not blank, make sure all tickers are strings (we have TRUE which otherwise becomes a boolean)
        '''
        f = vectorize(lambda x: True if x == 'SELL' or x == 'BUY' else False)
        self.table = self.table[f(self.table.direction)]
        if self.table.shape[0] > 0:
            self.table.ticker = vectorize(str)(self.table.ticker)
            self.table.ticker = vectorize(str.upper)(self.table.ticker)

    def check_for_data_errors(self):
        # nan only allowed in Target Position, everything else should have a value
        cols = list(self.table)
        cols.remove('tgt_position')
        for i in cols:
            if self.table.loc[:,i].isnull().values.any():
                UI.error_exit('Your Excel file has an error in "' + self.strat + '" file, "' + self.sheet + '" sheet, "'   + i + '" column. Fix it and try again.')

    def execute(self):
        self.load_from_excel()
        self.rename_columns()
        self.add_computed_columns()
        self.one_off_adjustments()
        self.clean_up()
        self.check_for_data_errors()
        return self.table, self.table_full
