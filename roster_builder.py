# from pdb import set_trace
import string
from numpy import in1d, vectorize
from codes_joint import *
from pandas import read_excel
import UI

class RosterBuilder(object):
    def __init__(self, input):
        self.output = input.copy()
        self.LL_earnings_overrides = []

    def get_table(self):
        return self.output

    def get_roster_type(self):
        return self.roster_type

    def get_order_type(self):
        return self.order_type

    def get_LL_earnings_overrides(self):
        return  self.LL_earnings_overrides

    def choose_roster_type(self):
        result = UI.get_multiple_choice_input(message = '''Choose roster type from the following:

type      type of order                             when to use
--------------------------------------------------------------------------------------------------------------------
A         combo                                     daily full rebalance at close
B         LOO                                       LL leftovers on open
C         LMT regular                               earnings or one-offs
D         LMT manual                                LL stocks
E         VWAP                                      daily full rebalance, early LL earnings exits, one-offs
F         MOC  ~~ ¡¡now with QMOC!! ~~              daily full rebalance on close
G         LMT regular 50%                           earnings only, ASSUMES ZERO CURRENT POSITION, NO FLIPS, NO LL CAP

    Default choice: F.
    Hit Enter to confirm, of type another one: >>   ''',
            options = ['A', 'B', 'C', 'D', 'E', 'F', 'G'], default = 'F')
        if result == 'B':
            print('  >>  ------ DON\'T FORGET TO REMOVE LL REVERSALS. ------')
        self.roster_type = result

    def confirm_order_type(self):
        default = ROSTER_DEFAULTS[self.roster_type]['order_type']
        message = 'Since you chose roster type ' + self.roster_type + ', we\'ll create orders as ' + default \
             + '. Hit Enter to confirm, or type order type you need (options are MOC, VWAP, LOO, LMT regular, LMT manual) >>   '
        self.order_type = UI.get_multiple_choice_input(message, ['MOC', 'VWAP', 'LOO', 'LMT regular', 'LMT manual'], default)

    def confirm_ticker_set(self):
        message = 'Enter tickers you need, separated by space, "--ALL" for all tickers with trades  >>   '
        if self.roster_type not in ['A', 'F']:
           self.tickers = UI.get_ticker_list(message)
        else:
            while True:
                confirm = input('Trades for all tickers will be generated. Hit Enter to confirm, or type "1" to select your own set of tickers  >>   ')
                if confirm == '':
                    self.tickers = ['--ALL']
                    break
                elif confirm == '1':
                    self.tickers = UI.get_ticker_list(message)
                    break
                else:
                    print('Invalid input, bro. Try again.')

    def remove_unneeded_tickers(self):
        if self.tickers != ['--ALL']:
            only_selected = self.output.loc[in1d(self.output.ticker.values, self.tickers), :]
            if len(only_selected) > 0:
                self.output = only_selected
            else:
                UI.error_exit('There were no trades in your Excel books for any of these tickers: ' + str(self.tickers))

    def impose_half_option(self):
        if self.roster_type == 'G':
            self.output.quantity = vectorize(int)(self.output.quantity / 2)

    def confirm_LL_cap(self):
        default = ROSTER_DEFAULTS[self.roster_type]['LL_cap_status']
        message = 'For ' + self.roster_type + '-type roster, LL cap by default is ' + default \
             + '. Hit Enter to confirm, or type your choice (1 for ON, 0 for OFF) >>   '
        answer_code = UI.get_multiple_choice_input(message, ['1', '0'], default)
        self.LL_cap_status = {'1' : 'ON', '0' : 'OFF', 'ON' : 'ON', 'OFF' : 'OFF'}[answer_code]

    def update_quantity_for_LL_choice(self):
        # making an extra copy of this field because it will be overwritten if LL cap is on, but we'll need it again for earnings exit override
        self.output['qty_full_backup'] = self.output.quantity
        if self.LL_cap_status == 'ON':
            self.output['LL_leftover_value'] = (self.output.quantity - self.output.qty_LL_on) * self.output.price
            self.output['cut_qty_to_LL_thold'] = (self.output.strategy != 'strat_1') | (self.output.LL_leftover_value > MIN_LL_LEFTOVER_VALUE)
            self.output.loc[self.output.cut_qty_to_LL_thold, 'quantity'] = self.output.loc[self.output.cut_qty_to_LL_thold, 'qty_LL_on']
        # if some trade quantities got replaced by zero (LL), remove those rows
        self.output = self.output[self.output.quantity > 0]

    def add_description(self):
        if self.roster_type == 'A':
            result = 'Full rebalance on close with VWAP/MOC'
        elif self.roster_type == 'B':
            result = 'Limit on open'
        elif self.roster_type == 'C':
            result = 'Limit regular during mkt hours'
        elif self.roster_type == 'D':
            result = 'Limit manual (LL)'
        elif self.roster_type == 'E':
            result = 'VWAP'
        elif self.roster_type == 'F':
            result = 'MOC'
        elif self.roster_type == 'G':
            result = 'Limit regular 50%'
        else:
            result = 'Custom:'

        if self.LL_cap_status == 'ON':
            result += ' LL capped '
        else:
            result += ' LL free '

        custom_message = input('Any custom message (reason for trade if unusual etc.)? And keep it short... >>   ')
        result += ''.join([i for i in custom_message if i in string.printable])
        self.output['description'] = result

    def override_LL_earnings_exits(self):
        if self.LL_cap_status == 'ON':
            earnings_exits = UI.get_ticker_list('We can override LL cap for earnings exits... So, any earnings exits that we should know about? Enter tickers separated by space. >>  ', blank_allowed = True)
            if len(earnings_exits) > 0:
                LL_trades = self.output.loc[self.output.low_liquidity == 1, 'ticker'].values.tolist()
                LL_override_tickers = list(set(earnings_exits).intersection(set(LL_trades)))
                self.output.loc[in1d(self.output.ticker, LL_override_tickers), 'quantity'] = self.output.loc[in1d(self.output.ticker, LL_override_tickers), 'qty_full_backup']
                self.output.loc[in1d(self.output.ticker, LL_override_tickers), 'description'] = EARNINGS_LL_OVERRIDE_TAG

                if len(LL_override_tickers) > 0:
                    self.LL_earnings_overrides = LL_override_tickers
                    print('  >>  OK, check this out... here is what we did (rightmost quantity is the one that will be submitted)')
                    print (self.output.loc[in1d(self.output.ticker, LL_override_tickers), ['strategy', 'ticker', 'low_liquidity', 'direction_human', 'qty_LL_on', 'quantity']])
                    input('Make sure this is correct... Hit Enter to continue.')

    def remove_active_orders(self):
        to_exclude = UI.get_ticker_list('Last question... Are there any tickers you\'d like to exclude from the roster? (e.g. active VWAPs). Enter them now separated by space, or hit Enter if none.  >>  ', blank_allowed = True)
        if len(to_exclude) > 0:
            self.output = self.output.loc[in1d(self.output.ticker.values, to_exclude, invert = True), :]

    def add_routes(self):
        if self.roster_type == 'A':
            self.output['route'] = ROUTES['VWAP']
            self.output.loc[self.output.strategy == 'strat_2', 'route'] = ROUTES['MOC']
        else:
            self.output['route'] = ROUTES[self.order_type]

    def add_schema(self):
        def f(direction, book, strategy, ticker, send_to_roster):
            if send_to_roster:
                if direction in ['5', '10']:
                    dir_string = 'SHORT'
                    direction_digit = '2'
                else:
                    dir_string = 'LONG'
                    direction_digit = '1'
                if strategy == 'consolidated':
                    perm = 'COMBO - ' + ticker + ' - ' + dir_string
                    temp = STRATEGY_CODES['combo'][book] + ' - ' + direction_digit +' NA'
                    alloc_sheet_string = STRATEGY_CODES['combo'][book] + ' - ' + direction_digit
                else:
                    perm = temp = alloc_sheet_string = STRATEGY_CODES[strategy][book] + ' - ' + dir_string
            else:
                perm = temp = alloc_sheet_string = 'ERROR DONT SEND'
            return (perm, temp, alloc_sheet_string)

        # set_trace()
        s = vectorize(f)(self.output.direction, self.output.book, self.output.strategy, self.output.ticker, self.output.send_to_roster)
        self.output['schema_permanent'] = s[0]
        self.output['schema_temporary'] = s[1]
        self.output['alloc_sheet_string'] = s[2]

    def add_pipe_codes(self):
        def f(direction, book, strategy, alloc_strat_2, alloc_strat_1, alloc_strat_3, alloc_strat_1_joint, alloc_strat_2_joint, alloc_strat_3_joint, alloc_Dual, alloc_strat_4):
            if strategy == 'consolidated':
                if direction in ['5', '10']:
                    dir_string = '2'
                else:
                    dir_string = '1'
                result = '|' + STRATEGY_CODES['strat_1'][book] + ',' + dir_string + ',' + str(alloc_strat_1)
                result += '|' + STRATEGY_CODES['strat_2'][book] + ',' + dir_string + ',' + str(alloc_strat_2)
                result += '|' + STRATEGY_CODES['strat_3'][book] + ',' + dir_string + ',' + str(alloc_strat_3)
                result += '|' + STRATEGY_CODES['strat_1_joint'][book] + ',' + dir_string + ',' + str(alloc_strat_1_joint)
                result += '|' + STRATEGY_CODES['strat_2_joint'][book] + ',' + dir_string + ',' + str(alloc_strat_2_joint)
                result += '|' + STRATEGY_CODES['strat_3_joint'][book] + ',' + dir_string + ',' + str(alloc_strat_3_joint)
                result += '|' + STRATEGY_CODES['dual'][book] + ',' + dir_string + ',' + str(alloc_Dual)
                result += '|' + STRATEGY_CODES['strat_4'][book] + ',' + dir_string + ',' + str(alloc_strat_4)
                result += '|,,'
                return result
            else:
                return ''
        self.output['pipe_code'] = vectorize(f)(self.output.direction, self.output.book, self.output.strategy, self.output.alloc_strat_2, self.output.alloc_strat_1, self.output.alloc_strat_3, self.output.alloc_strat_1_joint, self.output.alloc_strat_2_joint, self.output.alloc_strat_3_joint, self.output.alloc_Dual, self.output.alloc_strat_4)

    def sort(self):
        self.output = self.output.sort_values(by = ['strategy', 'book', 'ticker', 'send_to_roster'])

    def execute(self):
        self.choose_roster_type()
        self.confirm_order_type()
        self.confirm_ticker_set()
        self.remove_unneeded_tickers()
        self.impose_half_option()
        self.confirm_LL_cap()
        self.update_quantity_for_LL_choice()
        self.add_description()
        self.override_LL_earnings_exits()
        self.remove_active_orders()
        self.add_routes()
        self.add_schema()
        self.add_pipe_codes()
        self.sort()

        return self
