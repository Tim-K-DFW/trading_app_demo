# from pdb import set_trace

import xlsxwriter
import numpy as np
import pandas as pd
import yaml
import pickle
from datetime import datetime
import win32com.client
import os

import UI
from codes_joint import *
from helpers import *

class TradeSummaryWriter(object):
    def __init__(self, curr_folder, roster, strategy_data, params, keep_excel):
        self.set_curr_folder(curr_folder)
        self.params = params
        # initialized with strategy_data(dict of strategy Excel files) and roster(trade roster generated earlier)
        # self.TEMP_load_strat_data()
        # self.TEMP_load_roster()
        self.roster = roster.output
        self.roster_type = roster.roster_type
        self.strategy_data = strategy_data
        self.keep_excel = keep_excel
        self.strategies = [i for i in list(self.roster.strategy.unique()) if i != 'consolidated']

    def set_curr_folder(self, folder):
        self.curr_folder = folder + OUTPUT_PATH
        os.chdir(self.curr_folder)

    def load_column_map(self):
        with open(CONFIG_PATH + 'trades_summary_columns.yml', 'r') as stream:
            self.column_map = yaml.full_load(stream)

    def load_g6(self):
        G6_PATH = '...'
        print('Loading G6... hang on...')
        sheet = pd.read_excel(G6_PATH, sheet_name='summary', header = None)
        self.g6 = sheet.copy().iloc[9:, :]
        self.g6.columns = sheet.copy().iloc[8, :]
        self.g6 = self.g6.loc[:, self.column_map['common']['from_G6'].values()]
        # column for earnings disablement in G6 is called "active manual" and its meaning is reverse of "disabled", so switching the values here
        # keeping column name the same until it gets switched in `create_strat_df`. Switching it there would be cleaner, but less efficient
        self.g6['active manual'] = (~self.g6['active manual'].astype(bool)).astype(int)
        # self.g6 = pd.read_csv('--temp_g6.csv')
        print('Done!')

    # # TEMP DEVELOPMENT
    # # =================================================
    # def TEMP_load_roster(self):
    #     self.roster = pd.read_csv('--roster.csv')

    # def TEMP_load_strat_data(self):
    #     with open('data_dump.pickle', 'rb') as f:
    #         self.strategy_data = pickle.load(f)
    # # =================================================

    def remove_extra_cols_from_roster(self):
        self.roster = self.roster.loc[:, self.column_map['common']['from_roster'].values()]

    def create_totals_df(self):
        def add_subtotals_to_pivot(df):
            # https://stackoverflow.com/questions/41383302/pivot-table-subtotals-in-pandas
            df = pd.concat([d.append(d.sum().rename((k, '--'))) for k, d in df.groupby(level=[0])])
            # removing subtotal for "total" created by pivot_table, and putting grand total on the bottom
            total_to_keep_id = list(df.index.values).index(('Total', ''))
            total_to_drop_id = list(df.index.values).index(('Total', '--'))
            new_idx = list(df.index.values[:total_to_keep_id]) + list(df.index.values[total_to_drop_id+1:]) + [df.index.values[total_to_keep_id]]
            return df.reindex(new_idx)

        tt = self.roster.copy()
        tt = tt.rename(index = str, columns =  {'direction_human' : 'direction', 'book' : 'sector'})
        tt = tt.loc[tt.strategy != 'consolidated']
        tt.price = np.vectorize(float)(tt.price)
        tt.todays_price_return = np.vectorize(float)(tt.todays_price_return)
        tt['dollar_value'] = tt.quantity * tt.price
        tt['dir_adjustment'] = 1
        tt.loc[tt.direction.isin(['Sell Short', 'Sell']), 'dir_adjustment'] = -1
        tt['value_dir_adj'] = np.vectorize(float)(tt.dollar_value * tt.dir_adjustment)
        tt['trades'] = 1
        tt['strategy_scope'] = 'by sector'
        tt.loc[np.vectorize(lambda i: '_joint' in i)(tt.strategy), 'strategy_scope'] = 'joint'

        tt['is_full_size'] = (tt.actual_shares == 0) | (tt.target_shares == 0) | (tt.reversal)
        if self.params['earnings_sheet_full_size_only']:
            tt1 = tt.loc[tt.is_full_size]
        else:
            tt1 = tt.copy()
        self.earnings = tt1.pivot_table(index = ['sector', 'ticker'], columns = ['strategy', 'direction'], values = ['todays_price_return'], aggfunc = 'mean', fill_value = 0)

        self.totals_by_strategy_condensed = tt.pivot_table(index = ['strategy'], columns = ['direction'], values = ['trades', 'value_dir_adj'], aggfunc = 'sum', fill_value = 0, margins = True, margins_name = 'Total')
        self.totals_by_sector_condensed = tt.pivot_table(index = ['sector'], columns = ['direction'], values = ['trades', 'value_dir_adj'], aggfunc = 'sum', fill_value = 0, margins = True, margins_name = 'Total')

        t1 = tt.pivot_table(index = ['strategy', 'sector'], columns = ['direction'], values = ['trades', 'value_dir_adj'], aggfunc = 'sum', fill_value = 0, margins = True, margins_name = 'Total')
        self.totals_by_strategy_full = add_subtotals_to_pivot(t1)
        t2 = tt.pivot_table(index = ['sector', 'strategy'], columns = ['direction'], values = ['trades', 'value_dir_adj'], aggfunc = 'sum', fill_value = 0, margins = True, margins_name = 'Total')
        self.totals_by_sector_full = add_subtotals_to_pivot(t2)

    def create_strat_df(self, strategy):
        ss = self.roster[self.roster.strategy == strategy]
        ss = ss.merge(self.g6, how = 'left', on = 'ticker')
        ss = ss.merge(self.strategy_data[strategy].loc[:, self.column_map[strategy]['from_strat_file'].values()], how = 'left', left_on = 'ticker', right_on = self.column_map[strategy]['from_strat_file']['ticker'])
        if self.column_map[strategy]['from_strat_file']['ticker'] != self.column_map['common']['from_roster']['ticker']:
            ss.drop(columns = self.column_map[strategy]['from_strat_file']['ticker'], inplace = True)
        ss['is_full_size'] = (ss.actual_shares == 0) | (ss.target_shares == 0) | (ss.reversal)
        if self.params['EOD_sheets_full_size_only']:
            ss = ss.loc[ss['is_full_size']]
        full_map = {**self.column_map['common']['from_roster'], **self.column_map['common']['from_G6'], **self.column_map[strategy]['from_strat_file']}
        reverse_map = {v:k for k, v in full_map.items()}
        ss.rename(index = str, columns = reverse_map, inplace = True)
        if 'position after LL + treshold filter' in full_map.keys():
            ss['position after LL + treshold filter'] = ss['position after LL + treshold filter'].fillna('')
            ss.decision = ss.decision.fillna('')
            ss['kicked out by LLTF'] = ss['position after LL + treshold filter'] != ss['decision']
        if 'negative FCF yield' in self.column_map[strategy]['computed']:
            ss['negative FCF yield'] = ss['FCF/EV'] < 0
        if '_joint' in strategy:
            ss['position_after_conflicts_and_filters'] = ss['position_after_conflicts_and_filters'].fillna('')
            ss['intra-Joint conflict'] = ss['position_after_conflicts_and_filters'] != ss['position after LL + treshold filter']

        ss.fillna(0, inplace = True)
        cols_display_list = ['sector', 'ticker'] + self.column_map[strategy]['display_order']
        if ss.shape[0] == 0:
            # blank DF will be checked in the main function
            res = ss
        else:
            res = ss.pivot_table(index = cols_display_list, columns = 'direction', values = 'todays price return')
            res['price_move_sorting'] = res.mean(axis = 1).abs()
            res.sort_values(by = ['sector', 'price_move_sorting'], ascending = [True, False], inplace = True)
            res.drop(columns = 'price_move_sorting', inplace = True)

        return res

    def initialize_excel_file(self):
        print('Building trade summary XLS and PDF... hang on...')
        self.formats = {}
        self.timestamp = datetime.now().strftime('%m-%d-%y_%H%M')
        self.excel_fn = '{}trade_summary_{}.xlsx'.format(self.curr_folder, self.timestamp)
        wb = xlsxwriter.Workbook(self.excel_fn)
        self.formats['title_fmt'] = wb.add_format({'align' : 'left', 'bold' : True, 'font_name' : 'Arial', 'font_size' : 18})
        self.formats['title_red_fmt'] = wb.add_format({'align' : 'left', 'italic' : True, 'font_name' : 'Arial', 'font_size' : 18, 'font_color' : 'red'})
        self.formats['title2_fmt'] = wb.add_format({'align' : 'left', 'font_name' : 'Arial', 'font_size' : 11, 'italic' : 'true'})
        self.formats['header_fmt'] = wb.add_format({'align' : 'center', 'valign' : 'vcenter', 'text_wrap' : True, 'top' : 1, 'bottom' : 1, 'bold' : True})
        self.formats['header_top_fmt'] = wb.add_format({'align' : 'center', 'valign' : 'vcenter', 'text_wrap' : True, 'bold' : True, 'bg_color' : '#c4dafc'})
        self.formats['header_bottom_fmt'] = wb.add_format({'align' : 'center', 'valign' : 'vcenter', 'text_wrap' : True, 'bold' : True, 'bg_color' : '#c4dafc'})
        self.formats['left_border_fmt'] = wb.add_format({'left' : 1})
        self.formats['conditional_red_fmt'] = wb.add_format({'bg_color':   '#FFC7CE', 'font_color': '#9C0006'})
        self.formats['percent_fmt'] = wb.add_format({'num_format': '0.00%;-0.00%;0.00%'})
        self.formats['decimal_fmt'] = wb.add_format({'num_format': '0.0000'})
        self.formats['dollar_fmt'] = wb.add_format({'num_format': '_([$$-en-US]* #,##0_);_([$$-en-US]* (#,##0);_([$$-en-US]* "-"_);_(@_)'})
        self.formats['EV_fmt'] = wb.add_format({'num_format': '_(* #,##0.0_)'})
        self.formats['id_fmt'] = wb.add_format({'num_format': '#,##0', 'align' : 'center'})
        self.formats['non_zero_percent_fmt'] = wb.add_format({'num_format': '0.00%;-0.00%;'})
        self.formats['non_zero_percent_left_border_fmt'] = wb.add_format({'num_format': '0.00%;-0.00%;', 'left' : 1})
        self.formats['orders_area_fmt'] = wb.add_format({'bg_color' : '#dde5ff'})
        self.formats['subtotals_fmt'] = wb.add_format({'bg_color' : '#c5cbcc'})
        self.formats['grand_total_fmt'] = wb.add_format({'bold' : True, 'bg_color' : '#c4dafc'})
        self.formats['total_cols_fmt'] = wb.add_format({'bg_color' : '#c4dafc'})
        self.file_handle = wb
    
    def add_earnings_sheet(self):
        wb = self.file_handle
        df = self.earnings
        title = 'Trades summary - combined (earnings view)'
        title2 = 'Generated {}'.format(datetime.now().strftime('%m/%d/%y %H:%M:%S'))

        SHIFT_RIGHT = 1 # adding index colum
        FIRST_ROW = 3
        last_row = df.shape[0] + 1 + FIRST_ROW
        first_data_column = len(df.index.names) + SHIFT_RIGHT

        ws = wb.add_worksheet('earnings')
        ws.hide_gridlines(2)
        ws.freeze_panes(FIRST_ROW + 2, 0)
        ws.set_paper(1)
        ws.set_portrait()
        ws.set_margins(.2, .2, .2, .2)
        ws.repeat_rows(0, FIRST_ROW + 1)
        ws.fit_to_pages(width = 1, height = 0)
        ws.set_column(1, 1, 20)

        # header 1 are blanks and strategy names, header 2 is sector, ticker and direction
        header1 = [''] * 3 + [i[1] for i in  df.columns.values]
        header1 = [header1[0]] + [header1[i] if header1[i] != header1[i-1] else '' for i in range(1,len(header1))]
        header2 = ['#'] + list(df.index.names) + [i[2] for i in list(df.columns)]
        new_strat_column_ids = list(np.where(np.array(header1) != '')[0])
        last_column = len(header2) - 1
        if self.params['earnings_sheet_full_size_only']:
            ws.write('I1', 'FULL-SIZE TRADES ONLY', self.formats['title_red_fmt'])
        ws.write('A1', title, self.formats['title_fmt'])
        ws.write('A2', title2, self.formats['title2_fmt'])
        ws.write_row(FIRST_ROW, 0, header1, self.formats['header_top_fmt'])
        ws.write_row(FIRST_ROW + 1, 0, header2, self.formats['header_bottom_fmt'])

        ws.write_column(FIRST_ROW + 2, 0, list(range(1,df.shape[0]+1)), self.formats['id_fmt'])
        for i, id_column in enumerate(df.index.names):
            i += SHIFT_RIGHT # after we added index column in front
            col_data = df.index.get_level_values(id_column).values
            col_data = [col_data[0]] + [col_data[i] if col_data[i] != col_data[i-1] else '.' for i in range(1,len(col_data))]
            ws.write_column(FIRST_ROW + 2, i, col_data)
        for i, id_column in enumerate(df.columns):
            col_data = df[id_column].fillna(0).values
            ws.write_column(FIRST_ROW + 2, first_data_column + i, col_data, self.formats['non_zero_percent_fmt'])
        ws.conditional_format(FIRST_ROW + 2, first_data_column, last_row, last_column, {'type': '3_color_scale', 'mid_color' : 'white'})

        for i in new_strat_column_ids:
            ws.conditional_format(FIRST_ROW, i, last_row, i, {'type': 'no_blanks', 'format': self.formats['left_border_fmt']})
        
    def add_totals_sheet(self, which_part):
        def write_totals_table(sheet_handle, first_row, df):
            first_col_of_value_section = int(df.shape[1] / 2 + 2)
            last_row = df.shape[0] + 1 + first_row
            headers = list(df.index.names)
            if df.index.nlevels == 1:
                headers.append('.')
            headers = headers + list(df.columns.get_level_values(1))
            ws.write_row(first_row, 0, headers, self.formats['header_fmt']) #add centered and bold format
            for i, id_column in enumerate(df.index.names):
                col_data = df.index.get_level_values(id_column).values
                # for top level of index, removing duplicates
                col_data = [col_data[0]] + [col_data[i] if col_data[i] != col_data[i-1] else '.' for i in range(1,len(col_data))]
                ws.write_column(first_row + 1, i, col_data)
            for i, id_column in enumerate(df['trades']):
                col_data = df['trades'][id_column].values
                ws.write_column(first_row + 1, i + 2, col_data, self.formats['id_fmt'])
            for i, id_column in enumerate(df['value_dir_adj']):
                col_data = df['value_dir_adj'][id_column].values
                ws.write_column(first_row + 1, i + first_col_of_value_section, col_data, self.formats['dollar_fmt'])
            ws.write(last_row - 1, 1, '--')
            ws.conditional_format(last_row - 1, 0, last_row - 1, 11, {'type': 'no_blanks', 'format': self.formats['grand_total_fmt']})
            # confirm blank for condensed table
            subtotal_row_ids = [i for i, j in enumerate(list(df.index.values)) if j[1] == '--']
            for i in subtotal_row_ids:
                ws.conditional_format(i + first_row + 1, 0, i + first_row + 1, 11, {'type': 'no_blanks', 'format': self.formats['subtotals_fmt']})
            
            ws.conditional_format(first_row, first_col_of_value_section - 1, last_row - 1, first_col_of_value_section - 1, {'type': 'no_blanks', 'format': self.formats['total_cols_fmt']})
            ws.conditional_format(first_row, df.shape[1] + 1, last_row - 1, df.shape[1] + 1, {'type': 'no_blanks', 'format': self.formats['total_cols_fmt']})

        wb = self.file_handle
        title = 'Trades summary - aggregated, by {}'.format('strategy' if which_part == 'by_strategy' else 'sector')
        title2 = 'Generated {}'.format(datetime.now().strftime('%m/%d/%y %H:%M:%S'))
        # add condensed tables
        df_condensed = self.totals_by_strategy_condensed if which_part == 'by_strategy' else self.totals_by_sector_condensed
        df_full = self.totals_by_strategy_full if which_part == 'by_strategy' else self.totals_by_sector_full
        ws = wb.add_worksheet(which_part)
        ws.hide_gridlines(2)
        ws.set_paper(1)
        ws.set_portrait()
        ws.set_margins(.2, .2, .2, .2)
        ws.fit_to_pages(width = 1, height = 0)
        ws.set_column(0, 1, 20)
        # make columns with dollar values wider, for variable table width
        section_width = int(df_condensed.shape[1] / 2)
        ws.set_column(section_width + 2, section_width * 2 + 1, 15)
        first_row_of_condensed = 3
        first_row_of_full = first_row_of_condensed + df_condensed.shape[0] + 3
        ws.write('A1', title, self.formats['title_fmt'])
        ws.write('A2', title2, self.formats['title2_fmt'])
        write_totals_table(ws, first_row_of_condensed, df_condensed)
        write_totals_table(ws, first_row_of_full, df_full)

    def add_strat_sheet(self, strategy, df):
        wb = self.file_handle

        title = '{}: Trades summary'.format(strategy.upper())
        title2 = 'Generated {}'.format(datetime.now().strftime('%m/%d/%y %H:%M:%S'))

        SHIFT_RIGHT = 1 # adding index colum

        # row of table header, 0-indexed
        FIRST_ROW = 3
        last_row = df.shape[0] + 1 + FIRST_ROW
        first_data_column = len(df.index.names) + SHIFT_RIGHT
        headers = ['#'] + list(df.index.names) + list(df.columns)

        ws = wb.add_worksheet(strategy)
        ws.hide_gridlines(2)
        ws.freeze_panes(FIRST_ROW + 1, 0)
        ws.set_paper(1)
        ws.set_portrait()
        ws.set_margins(.2, .2, .2, .2)
        ws.repeat_rows(0, FIRST_ROW)
        ws.fit_to_pages(width = 1, height = 0)
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 20)

        ws.write('A1', title, self.formats['title_fmt'])
        ws.write('A2', title2, self.formats['title2_fmt'])
        if self.params['EOD_sheets_full_size_only']:
            ws.write('I1', 'FULL-SIZE TRADES ONLY', self.formats['title_red_fmt'])
        ws.write_row(FIRST_ROW, 0, headers, self.formats['header_fmt']) #add centered and bold format

        # write 1-indexed count
        ws.write_column(FIRST_ROW + 1, 0, list(range(1,df.shape[0]+1)), self.formats['id_fmt'])

        # write strategy logic (from DF's index)
        for i, id_column in enumerate(df.index.names):
            i += SHIFT_RIGHT # after we added index column in front
            col_data = df.index.get_level_values(id_column).values

            if id_column in ['EV', 'EV 10d avg']:
                ws.set_column(i, i, 11)
                ws.write_column(FIRST_ROW + 1, i, col_data, self.formats['EV_fmt'])
            elif ((col_data==0) | (col_data==1)).all():
                # True/False or 1/0
                col_data = col_data.astype(int)
                ws.conditional_format(FIRST_ROW + 1, i, last_row, i, {'type': 'cell', 'criteria': '==', 'value': 1, 'format': self.formats['conditional_red_fmt']})
                ws.write_column(FIRST_ROW + 1, i, col_data)
            elif np.issubdtype(col_data.dtype, np.number):
                # assuming all numeric columns other than z-score are percent but can add other special cases depending on column name
                if id_column == 'Zscore':
                    ws.write_column(FIRST_ROW + 1, i, col_data, self.formats['decimal_fmt'])
                else:
                    ws.write_column(FIRST_ROW + 1, i, col_data, self.formats['percent_fmt'])
            else:
                # remove duplicates for top-level index
                if id_column in ['sector', 'strategy']:
                    col_data = [col_data[0]] + [col_data[i] if col_data[i] != col_data[i-1] else '.' for i in range(1,len(col_data))]
                ws.write_column(FIRST_ROW + 1, i, col_data)

        # write todays price return (from DF's columns)
        for i, id_column in enumerate(df.columns):
            col_data = df[id_column].fillna(0).values
            ws.write_column(FIRST_ROW + 1, first_data_column + i, col_data, self.formats['non_zero_percent_fmt'])

        ws.conditional_format(FIRST_ROW + 1, first_data_column, last_row, first_data_column + 3, {'type': '3_color_scale', 'mid_color' : 'white'})
        ws.conditional_format(FIRST_ROW, first_data_column, FIRST_ROW, first_data_column + 3, {'type': 'no_blanks', 'format': self.formats['total_cols_fmt']})


    # def reorder_sheets(self):
    #     # move earnings sheet to the end if it's an EOD roster
    #     if self.roster_type in ['A', 'F']:
    #         self.file_handle.worksheets_objs = self.file_handle.worksheets_objs[1:] + [self.file_handle.worksheets_objs[0]]

    def save_excel_file(self):
        self.file_handle.close()

    def save_to_PDF(self):
        create_PDF = UI.get_multiple_choice_input('We will not be creating PDF summary of trades. Hit Enter to confirm or enter 1 if you still want that PDF... but be aware that if you do that, all your Excel files will get totally closed. >>  ', ['1', '0'], '0')
        if create_PDF == '1':
            xl = win32com.client.Dispatch("Excel.Application")
            xl.Visible = False
            wb = xl.Workbooks.Open(self.excel_fn)
            wb.WorkSheets.Select()
            self.path_to_pdf = '{}trade_summary_{}.pdf'.format(self.curr_folder, self.timestamp)
            wb.ActiveSheet.ExportAsFixedFormat(0, self.path_to_pdf)
            wb.Close()
            print('Done!')
            # if enabled, closes all instances of Excel, not only one it has opened
            xl.Quit()

    def delete_excel_file(self):
        pass

    def done_message(self):
        print('  >>  Trade summary in Excel (and possibly PDF) versions is saved in the same folder with the rest.')

    def execute(self):
        self.load_column_map()
        self.load_g6()
        self.remove_extra_cols_from_roster()
        self.create_totals_df()
        self.initialize_excel_file()
        self.add_totals_sheet('by_strategy')
        self.add_totals_sheet('by_sector')
        for s in self.strategies:
            pivot_df = self.create_strat_df(s)
            if pivot_df.shape[0] > 0:
                self.add_strat_sheet(s, pivot_df)
        self.add_earnings_sheet()
        # manually moving sheets breaks pagination settings for all sheets
        # self.reorder_sheets()
        self.save_excel_file()
        self.save_to_PDF()
        if self.keep_excel == False:
            self.delete_excel_file()
        self.done_message()
