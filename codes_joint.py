from pandas import read_excel
from numpy import vectorize
# from pdb import set_trace

CURRENT_PATH = '...'
CONFIG_PATH = '...'
OUTPUT_PATH = '---Batch Trade Submission\\'

trade_codes = {'long' : {'BUY' : '1', 'SELL' : '2'}, 'short' : {'BUY' : '10', 'SELL' : '5'}}
DIRECTION_CODES = {'1' : 1_trade_codes}
DIRECTION_CODES_REVERSE = {'1' : 'Buy', '2' : 'Sell', '5' : 'Sell Short', '10' : 'Buy to Cover'}

MIN_LL_LEFTOVER_VALUE = 25000

CONSOLIDATION_CASES = {'J': [['Buy', 'Buy'], ['Sell', 'Sell'], ['Buy to Cover', 'Buy to Cover'], ['Sell Short', 'Sell Short']],
    # 'K' : [['Buy', 'Buy to Cover'], ['Buy to Cover', 'Buy']],             K type not suppored ty the OMS as of 10/15/18
    'L' : [['Buy', 'Sell'], ['Sell', 'Buy'], ['Buy to Cover', 'Sell Short'], ['Sell Short', 'Buy to Cover']]}

FLIP_CONS_CASES = {
    'F1' : {'Sell' : 1, 'Sell Short' : 2},
    'F2' : {'Sell' : 2, 'Sell Short' : 1},
    'F3' : {'Sell' : 2, 'Sell Short' : 2},
    'F4' : {'Buy' : 2, 'Buy to Cover' : 1},
    'F5' : {'Buy' : 1, 'Buy to Cover' : 2},
    'F6' : {'Buy' : 2, 'Buy to Cover' : 2}}


# old_strat_1_file_cells = {'first_row' : 7, 'cols_to_load' : 82, 'univ_size' : (0, 6)}
strat_1_file_cells = {'first_row' : 11, 'cols_to_load' : 129, 'univ_size' : (4, 7)}
strat_2_file_cells = {'first_row' : 11, 'cols_to_load' : 129, 'univ_size' : (4, 8)}
strat_3_file_cells = strat_1_joint_file_cells = strat_3_joint_file_cells = strat_2_joint_file_cells = dual_file_cells = {'first_row' : 11, 'cols_to_load' : 129, 'univ_size' : (5, 4)}
strat_4_file_cells = {'first_row' : 11, 'cols_to_load' : 40, 'univ_size' : (2, 1)}


SOURCE_FILES = {
    'strat_1' : {'file': 'strategy strat_1.xlsx', 'sheet' : 'Summary', 'strat' : 'strat_1', 'cells' : strat_1_file_cells},
    'strat_3' : {'file': 'strategy strat_3.xlsx', 'sheet' : 'Summary', 'strat' : 'strat_3', 'cells' : strat_3_file_cells},
    'strat_2' : {'file': 'strategy strat_2.xlsx', 'sheet' : 'Summary', 'strat' : 'strat_2', 'cells' :strat_2_file_cells},
    'strat_1_joint' : {'file': 'strategy JOINT.xlsx', 'sheet' : 'strat_1', 'strat' : 'strat_1_joint', 'cells' : strat_1_joint_file_cells},
    'strat_3_joint' : {'file': 'strategy JOINT.xlsx', 'sheet' : 'strat_3', 'strat' : 'strat_3_joint', 'cells' : strat_3_joint_file_cells},
    'strat_2_joint' : {'file': 'strategy JOINT.xlsx', 'sheet' : 'strat_2', 'strat' : 'strat_2_joint', 'cells' :strat_2_joint_file_cells},
    'dual' : {'file': 'strategy DUAL.xlsx', 'sheet' : 'Summary', 'strat' : 'dual', 'cells' :dual_file_cells},
    'strat_4' : {'file': 'strategy strat_4.xlsm', 'sheet' : 'Summary', 'strat' : 'strat_4', 'cells' :strat_4_file_cells}
}

# strat codes are linked to `book` field which is pulled from portfolio_mapping
# 'CFSTPL' does not exist, here only for testing
strat_1_strat_codes = {'staples' : 'CFSTPL', 'discretionary' : 'CFCONS', 'healthcare' : 'CFHLTH', 'technology' : 'CFTECH', 'industrials' : 'CFINDU'}
strat_3_strat_codes = {'staples' : 'JPSTPL', 'discretionary' : 'JPCONS', 'healthcare' : 'JPHLTH', 'technology' : 'JPTECH', 'industrials' : 'JPINDU'}
strat_2_strat_codes = {'staples' : 'SLSTPL', 'discretionary' : 'SLCONS', 'healthcare' : 'SLHLTH', 'technology' : 'SLTECH', 'industrials' : 'SLINDU', 'financials' : 'SLFINA', 'REIT' : 'SLREIT'}
# joint strategies don't have a notion of sector, but we keep this partition for compatibility... so identical code for all "sectors"
strat_1_joint_strat_codes = {k : 'CFJOIN' for k in strat_2_strat_codes.keys()}
strat_3_joint_strat_codes = {k : 'JPJOIN' for k in strat_2_strat_codes.keys()}
strat_2_joint_strat_codes = {k : 'SLJOIN' for k in strat_2_strat_codes.keys()}
dual_strat_codes = {k : 'DUAL' for k in strat_2_strat_codes.keys()}
strat_4_strat_codes = {k : 'SQRLJN' for k in strat_2_strat_codes.keys()}; strat_4_strat_codes['strat_4 - unassigned'] = 'SQRLJN'
combo_strat_codes = {'staples' : 'STPL', 'discretionary' : 'CONS', 'healthcare' : 'HLTH', 'technology' : 'TECH', 'industrials' : 'INDU', 'financials' : 'FINA', 'REIT' : 'REIT'}
# has to have all strategies + "combo" - its lenght is used in trade_generator#add_consolidation_tags
STRATEGY_CODES = {'strat_1' : strat_1_strat_codes, 'strat_3' : strat_3_strat_codes, 'strat_2' : strat_2_strat_codes,
    'strat_1_joint' : strat_1_joint_strat_codes, 'strat_3_joint' : strat_3_joint_strat_codes, 'strat_2_joint' : strat_2_joint_strat_codes,
    'dual' : dual_strat_codes, 'strat_4' : strat_4_strat_codes, 'combo' : combo_strat_codes}
ROSTER_CODES = {'roster': {'A' : 'MOC_full', 'B' : 'MOC_LL_half', 'C' : 'LMT_half_EARNINGS', 'D' : 'LMT_LL_leftovers',  'E' : 'LMT_full_OTHER'},
    'csv' : {'A' : 'MOC-VWAP', 'B' : 'LOO', 'C' : 'LMT_regular', 'D' : 'LMT_LL', 'E' : 'VWAP', 'F' : 'MOC', 'G' : 'LMTreg50pct'}}

# standard MOC (used prior to 1/22/19) is 'MLCO3-MC'
ROUTES = {'MOC' : '...', 'LMT regular' : '...', 'LMT manual' : '...', 'LOO' : '...', 'VWAP' : '...', 'LMT regular 50pct' : '...'}

ROSTER_DEFAULTS = {
    'A' : {'order_type': 'MOC/VWAP', 'LL_cap_status' : 'ON'},
    'B' : {'order_type': 'LOO', 'LL_cap_status' : 'OFF'},
    'C' : {'order_type': 'LMT regular', 'LL_cap_status' : 'OFF'},
    'D' : {'order_type': 'LMT manual', 'LL_cap_status' : 'OFF'},
    'E' : {'order_type': 'VWAP', 'LL_cap_status' : 'OFF'},
    'F' : {'order_type': 'MOC', 'LL_cap_status' : 'ON'},
    'G' : {'order_type': 'LMT regular 50pct', 'LL_cap_status' : 'OFF'}
}

EARNINGS_LL_OVERRIDE_TAG = 'earnings exit LL cap override'

def load_portfolio_mapping():
    sheet = read_excel(CURRENT_PATH + 'portfolio mapping.xlsx', sheet_name = '1', usecols = 7)
    sheet = sheet.iloc[:, 3:6]
    sheet.columns = ['broker_ticker', 'fs_ticker', 'book']
    sheet.broker_ticker = vectorize(str)(sheet.broker_ticker)
    sheet.broker_ticker = vectorize(str.upper)(sheet.broker_ticker)
    sheet.fs_ticker = vectorize(str)(sheet.fs_ticker)
    sheet.fs_ticker = vectorize(str.upper)(sheet.fs_ticker)
    return sheet

PORTFOLIO_MAPPING = load_portfolio_mapping()
