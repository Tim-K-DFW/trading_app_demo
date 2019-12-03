# from pdb import set_trace

import sys
import pandas as pd
from pandas import concat, read_csv
from codes_joint import *
import helpers
import UI

# custom classes, each in own file
from file_reader import FileReader
from trade_generator import TradeGenerator
from roster_builder import RosterBuilder
from roster_writer import RosterWriter
from trade_summary_writer import TradeSummaryWriter

pd.set_option('display.max_columns', 500)


def confirm_strategy():
    temp_dict = {str(k):v for (k, v) in zip(range(1,len(STRATEGY_CODES)), list(STRATEGY_CODES.keys())[:-1])}
    temp_dict[str(len(STRATEGY_CODES))] = list(temp_dict.values())
    temp_dict[str(len(STRATEGY_CODES) + 1)] = list(temp_dict.values())[-1][:-1]
    message = '''We\'ll generate rosters for all your "strategies". Hit Enter to accept, or type strategy you need:
        1       strat_1
        2       strat_2
        3       strat_3
        4       strat_4
        5       strat_5
        6       strat_6
        7       strat_7
        8       strat_8
        9       all
        10      all ex strat_8 (earnings?)  >>   '''
    code = UI.get_multiple_choice_input(message, list(temp_dict.keys()), '9')
    return [temp_dict[code]] if isinstance(temp_dict[code], str) else temp_dict[code]

def load_from_books(path, args):
    table = []
    table_full = {}
    strat_selected = confirm_strategy()
    for i in [j for j in SOURCE_FILES.values() if j['strat'] in strat_selected]:
        curr_table, curr_full_table = FileReader(dict = i, curr_folder = path, args = args).execute()
        table.append(curr_table)
        table_full[i['strat']] = curr_full_table

    assert sum([list(table[i]) == list(table[0]) for i in range(len(table))]) == len(table), \
        'Mismatch between column names, make sure all "_file_columns" dictionaries have same keys in same order'
    return {'trades_only': concat(table, ignore_index = True), 'full_table' : table_full}

def main():
    # changes curr div to argv[1] if any provided AND return argv[1] so we can pass it to classes. can be used for debugging
    # curr_dir = helpers.set_working_dir()

    # set_trace()
    if '-nocheck' not in sys.argv:
        UI.greeting()
    strategy_data = load_from_books(CURRENT_PATH, args = sys.argv)
    trades_from_Excel = strategy_data['trades_only']
    trades_for_roster = TradeGenerator(trades_from_Excel).execute()
    # roster object in addition to actual table, stores other properties (type, LL etc.)
    roster = RosterBuilder(trades_for_roster).execute()
    if '-noout' not in sys.argv:
        RosterWriter(roster, CURRENT_PATH).execute()
    TradeSummaryWriter(CURRENT_PATH, keep_excel = True, params = {'EOD_sheets_full_size_only' : True, 'earnings_sheet_full_size_only' : True}, roster = roster, strategy_data = strategy_data['full_table']).execute()
    if roster.roster_type in ['F', 'A']:
        helpers.save_strategy_files()
    UI.show_done_message()

    # for testing
    # while True:
    #     roster = RosterBuilder(trades_for_roster).execute()
    #     RosterWriter(roster, CURRENT_PATH).execute()
    #     UI.show_done_message()

    #     again = UI.get_multiple_choice_input('Wanna try to create a different roster? No reload time... (0 for No, 1 or Enter for Yes)  >>   ', ['0', '1'], ['1'])
    #     if again == '0':
    #         break

main()


# ----------------------------------------------------------------------
# for testing

# tt = FileReader(SOURCE_FILES['strat_1'], CURRENT_PATH)
# tt.load_from_excel()
# tt.rename_columns()
# tt.add_computed_columns()
# tt.clean_up()
# oo = tt.table
