from sys import argv, exit
import shutil
import os
from warnings import catch_warnings, filterwarnings, simplefilter
from numpy import vectorize
from codes_joint import *

with catch_warnings():
    filterwarnings("ignore",category=DeprecationWarning)
    from openpyxl import load_workbook

# def set_working_folder:
#     return DEFAULT_PATH if len(argv) == 1 else argv[1]

v_int = vectorize(int)


# R-like `match`; requires list-type b (larger list)
match = lambda a, b: [ b.index(x) if x in b else None for x in a ]

def read_series_xlsx(sheet, cell_range):
    return [t[0].value for t in sheet[cell_range]]

def write_column_xlsx(sheet, col_letter, starting_row, values, update_to_currency = False):
    for id, value in enumerate(values):
        tgt_row = starting_row + id
        sheet[col_letter + str(tgt_row)].value = value
        if update_to_currency:
            sheet[col_letter + str(tgt_row)].number_format = '_("$"* #,##0.00_)_("$"* \\(#,##0.00\\)_("$"* "-"??_)_(@_)'

def save_strategy_files():
    for f in list(set([v['file'] for v in SOURCE_FILES.values()])):
        src = CURRENT_PATH + f
        dst = CURRENT_PATH + '---Manual backup\\--before close daily\\' + f
        shutil.copy(src, dst)
        print('  >>  {} saved to ---Manual backup\--before close daily'.format(f))


# not used, all files are being read and written with full paths
# def set_working_dir():
#     result = default_directory if len(argv) == 1 else argv[1]
#     os.chdir(result)
#     return result
