import pandas as pd
import pytest
import trade_generator as tg
from roster_builder import RosterBuilder
from pdb import set_trace
from helpers import *
from codes_joint import *
from numpy import sign, vectorize

test_df = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'all')
tt = tg.TradeGenerator(test_df)
tt.add_trading_platform()
tt.fill_adj_direction()
tt.compute_flips()
tt.fill_LL_caps()
tt.fold_flips_to_new_rows()
tt.add_human_readable_direction()
# consolidate_strategies()
# not loading consolidate_strategies() here because they use different test inputs
tt.add_portfolio_mapping_columns()
tt.add_limit_price()

def test_gets_initiated_with_df():
    assert type(tt.input) == pd.core.frame.DataFrame

# def test_exit_if_no_trades(capsys):
#     test_df = pd.read_csv('tt.csv')
#     test_df = test_df.iloc[0:0]
#     tt = tg.TradeGenerator(test_df)
#     tt.exit_if_no_trades()
#     out, err = capsys.readouterr()
#     assert 'No trades for the specified tickers in the specified books' in out

def test_add_trading_platform():
    assert tt.output.trading_platform[5] == 'BBT'

def test_fill_adj_direction():
    assert tt.output.dir_adj_long[0] == '2'
    assert tt.output.dir_adj_long[1] == '1'
    assert tt.output.dir_adj_short[0] == '5'
    assert tt.output.dir_adj_short[1] == '10'

def test_compute_flips_regular():
    # test split into flips, before LL caps are added
    answers = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'regular flips')

    assert int(tt.output.first_leg[0]) == answers['1st_leg_dir'][0]
    assert int(tt.output.second_leg[0]) == answers['2nd_leg_dir'][0]
    assert int(tt.output.amount_1st_leg[0]) == answers['1st_leg_qty'][0]
    assert int(tt.output.amount_2nd_leg[0]) == answers['2nd_leg_qty'][0]

    assert int(tt.output.first_leg[1]) == answers['1st_leg_dir'][1]
    assert int(tt.output.second_leg[1]) == answers['2nd_leg_dir'][1]
    assert int(tt.output.amount_1st_leg[1]) == answers['1st_leg_qty'][1]
    assert int(tt.output.amount_2nd_leg[1]) == answers['2nd_leg_qty'][1]

    assert int(tt.output.first_leg[2]) == answers['1st_leg_dir'][2]
    assert int(tt.output.second_leg[2]) == answers['2nd_leg_dir'][2]
    assert int(tt.output.amount_1st_leg[2]) == answers['1st_leg_qty'][2]
    assert int(tt.output.amount_2nd_leg[2]) == answers['2nd_leg_qty'][2]

    assert int(tt.output.first_leg[3]) == answers['1st_leg_dir'][3]
    assert int(tt.output.second_leg[3]) == answers['2nd_leg_dir'][3]
    assert int(tt.output.amount_1st_leg[3]) == answers['1st_leg_qty'][3]
    assert int(tt.output.amount_2nd_leg[3]) == answers['2nd_leg_qty'][3]

def test_fill_LL_caps():
    # tests addition of LL caps (new columns), immediately following `compute_flips`
    tt.fill_LL_caps()
    answers = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'LL flips')

    assert int(tt.output.amount_1st_leg_LL_on[0]) == answers['1st_leg_qty_LL_on'][0]
    assert int(tt.output.amount_2nd_leg_LL_on[0]) == answers['2nd_leg_qty_LL_on'][0]
    assert int(tt.output.amount_1st_leg_LL_on[1]) == answers['1st_leg_qty_LL_on'][1]
    assert int(tt.output.amount_2nd_leg_LL_on[1]) == answers['2nd_leg_qty_LL_on'][1]
    assert int(tt.output.amount_1st_leg_LL_on[2]) == answers['1st_leg_qty_LL_on'][2]
    assert int(tt.output.amount_2nd_leg_LL_on[2]) == answers['2nd_leg_qty_LL_on'][2]
    assert int(tt.output.amount_1st_leg_LL_on[3]) == answers['1st_leg_qty_LL_on'][3]
    assert int(tt.output.amount_2nd_leg_LL_on[3]) == answers['2nd_leg_qty_LL_on'][3]
    assert int(tt.output.amount_1st_leg_LL_on[4]) == answers['1st_leg_qty_LL_on'][4]
    assert int(tt.output.amount_2nd_leg_LL_on[4]) == answers['2nd_leg_qty_LL_on'][4]

    assert int(tt.output.amount_1st_leg_LL_on[5]) == answers['1st_leg_qty_LL_on'][5]
    assert int(tt.output.amount_2nd_leg_LL_on[5]) == answers['2nd_leg_qty_LL_on'][5]

def test_fold_flips():
    assert list(tt.output.ticker).count('BFB') == 2
    assert list(tt.output.ticker).count('IBM') == 2
    assert list(tt.output.ticker).count('AIR') == 2
    assert list(tt.output.ticker).count('AEO') == 2
    assert list(tt.output.ticker).count('APEI') == 2
    assert list(tt.output.ticker).count('AZO') == 2

    assert list(tt.output.ticker).count('BBY') == 1
    assert list(tt.output.ticker).count('CCL') == 1
    assert list(tt.output.ticker).count('BIG') == 1
    assert list(tt.output.ticker).count('CMCSA') == 1
    assert list(tt.output.ticker).count('CBRL') == 1

def test_add_human_readable_direction():
    assert tt.output.direction_human[0] == 'Sell'
    assert tt.output.direction_human[1] == 'Buy to Cover'
    assert tt.output.direction_human[11] == 'Sell'
    assert tt.output.direction_human[12] == 'Buy'

def test_consolidation_type():
    test_df = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'consolidation - determine type')
    tt = tg.TradeGenerator(test_df)
    tt.output = test_df.iloc[:,:35]
    tt.output.first_leg = vectorize(str)(vectorize(int)(list(tt.output.first_leg)))
    tt.add_human_readable_direction()
    tt.add_consolidation_tags()
    assert sum(test_df.ANS_cons_type == tt.output.cons_type) == tt.output.shape[0]
    assert sum(test_df.ANS_cons_ID == tt.output.cons_id) == tt.output.shape[0]

def test_consolidate_J_rule():
    test_df = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'consolidation - cat J')
    tt = tg.TradeGenerator(test_df)
    tt.output = test_df.iloc[:12,:35]
    tt.output.first_leg = vectorize(str)(vectorize(int)(list(tt.output.first_leg)))
    tt.add_human_readable_direction()
    tt.add_consolidation_tags()
    tt.consolidate_strategies('1')

    assert sum(tt.output.cons_type == test_df.ANS_cons_type) == test_df.shape[0]
    assert sum(tt.output.cons_id == test_df.ANS_cons_ID) == test_df.shape[0]
    assert sum(tt.output.send_to_roster == test_df.ANS_send_to_roster) == test_df.shape[0]
    assert sum(tt.output.send_to_sheet == test_df.ANS_show_in_sheet) == test_df.shape[0]
    assert sum(tt.output.combo_schema == test_df.ANS_combo_schema) == test_df.shape[0]
    assert sum(tt.output.strategy == test_df.strategy) == test_df.shape[0]
    assert sum(tt.output.alloc_strat_2 == test_df.ANS_alloc_J) == test_df.shape[0]
    assert sum(tt.output.alloc_strat_1 == test_df.ANS_alloc_P) == test_df.shape[0]
    assert sum(tt.output.amount_1st_leg == test_df.ANS_qty) == test_df.shape[0]
    assert sum(tt.output.first_leg == vectorize(str)(test_df.ANS_dir)) == test_df.shape[0]

def test_consolidate_L_rule():
    test_df = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'consolidation - cat L')
    tt = tg.TradeGenerator(test_df)
    tt.output = test_df.iloc[:28,:35]
    tt.output.first_leg = vectorize(str)(vectorize(int)(list(tt.output.first_leg)))
    tt.add_human_readable_direction()
    tt.consolidate_strategies('1')

    assert sum(tt.output.cons_type == test_df.ANS_cons_type) == test_df.shape[0]
    assert sum(tt.output.cons_id == test_df.ANS_cons_ID) == test_df.shape[0]
    assert sum(tt.output.send_to_roster == test_df.ANS_send_to_roster) == test_df.shape[0]
    assert sum(tt.output.send_to_sheet == test_df.ANS_show_in_sheet) == test_df.shape[0]
    assert sum(tt.output.combo_schema == test_df.ANS_combo_schema) == test_df.shape[0]
    assert sum(tt.output.alloc_strat_2 == test_df.ANS_alloc_J) == test_df.shape[0]
    assert sum(tt.output.alloc_strat_1 == test_df.ANS_alloc_P) == test_df.shape[0]
    assert sum(tt.output.amount_1st_leg == test_df.ANS_qty) == test_df.shape[0]
    assert sum(tt.output.first_leg == vectorize(str)(test_df.ANS_dir)) == test_df.shape[0]
    assert sum(tt.output.strategy == vectorize(str)(test_df.strategy)) == test_df.shape[0]

def test_consolidate_flips():
    test_df = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'consolidation - flips')
    tt = tg.TradeGenerator(test_df)
    tt.output = test_df.iloc[:22,:35]
    tt.output.first_leg = vectorize(str)(vectorize(int)(list(tt.output.first_leg)))
    tt.add_human_readable_direction()
    tt.add_consolidation_tags()
    tt.consolidate_strategies('1')

    assert sum(tt.output.cons_type == test_df.ANS_cons_type) == test_df.shape[0]
    assert sum(tt.output.cons_id == test_df.ANS_cons_ID) == test_df.shape[0]
    assert sum(tt.output.send_to_roster == test_df.ANS_send_to_roster) == test_df.shape[0]
    assert sum(tt.output.send_to_sheet == test_df.ANS_show_in_sheet) == test_df.shape[0]
    assert sum(tt.output.combo_schema == test_df.ANS_combo_schema) == test_df.shape[0]
    assert sum(tt.output.alloc_strat_2 == test_df.ANS_alloc_J) == test_df.shape[0]
    assert sum(tt.output.alloc_strat_1 == test_df.ANS_alloc_P) == test_df.shape[0]
    assert sum(tt.output.amount_1st_leg == test_df.ANS_qty) == test_df.shape[0]
    assert sum(tt.output.first_leg == vectorize(str)(test_df.ANS_dir)) == test_df.shape[0]
    assert sum(tt.output.strategy == vectorize(str)(test_df.ANS_strategy)) == test_df.shape[0]

def test_add_portfolio_mapping_columns():
    tt.add_portfolio_mapping_columns()

    assert tt.output.book[0] == 'staples'
    assert tt.output.book[1] == 'technology'
    assert tt.output.book[2] == 'industrials'

    assert tt.output.broker_ticker[0] == 'BF/B'
    assert tt.output.broker_ticker[1] == 'IBM'

# def test_add_portfolio_mapping_columns_error():
    # can't figure out how to test actual output and exit quickly, so only the filter
    # tt.output.loc[0, 'ticker'] = 'NOSUCHTICKER'
    # output = tt.add_portfolio_mapping_columns()
    # set_trace()
    # assert output == '???'

def test_add_limit_price():
    assert tt.output.limit_price[0] == 53.15
    assert tt.output.limit_price[2] == 63.92

def test_final_cleanup():
    # don't move this method to the outside, because it removes many intermediate columns used in previous tests
    tt.consolidate_strategies('1')
    tt.final_cleanup()
    assert 'quantity' in list(tt.output)
    assert 'qty_LL_on' in list(tt.output)
    assert len(tt.output[tt.output.quantity == 0]) == 0

def test_add_schemas():
    test_df = pd.read_excel('excel_files\\trade_gen_tests.xlsx', sheet_name = 'add_schema')
    tt = RosterBuilder(test_df.iloc[:, :32])
    tt.roster_type = 'A'
    tt.order_type = 'MOC/VWAP'
    tt.add_routes()
    tt.add_schema()
    tt.add_pipe_codes()

    assert len(tt.output.schema_permanent == test_df.ANS_perm_schema) == tt.output.shape[0]
    assert len(tt.output.schema_temporary == test_df.ANS_temp_schema) == tt.output.shape[0]
    assert len(tt.output.pipe_code == test_df.ANS_pipe_code) == tt.output.shape[0]
