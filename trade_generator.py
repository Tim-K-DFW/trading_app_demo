# from pdb import set_trace
from pandas import DataFrame, concat, read_excel, read_csv
from numpy import vectorize, sign, where, array
from helpers import *
from codes_joint import *
import UI

class TradeGenerator(object):
    def __init__(self, input_df):
        self.input = input_df
        self.output = input_df.copy()

    def exit_if_no_trades(self):
        # not tested, takes too long to figure out i/o testing
        if len(self.input) == 0:
            print()
            print('  >>  No trades for the specified tickers in the specified books')
            input('  >>  Hit Enter to exit')
            exit()

    def add_trading_platform(self):
        self.output['trading_platform'] = 'BBT'

    def fill_adj_direction(self):
        # adds target-specific directions - "buy" and "buy to cover", "sell" and "sell short"
        adj_direction = lambda platform, l_s, direction: DIRECTION_CODES[platform][l_s][direction]
        self.output['dir_adj_long'] = vectorize(adj_direction)(self.output.trading_platform, 'long', self.output.direction)
        self.output['dir_adj_short'] = vectorize(adj_direction)(self.output.trading_platform, 'short', self.output.direction)

    def compute_flips(self):
        self.output['curr_negative'] = self.output.actual_shares < 0
        self.output['target_negative'] = self.output.target_shares < 0
        self.output['reversal'] = (sign(self.output.actual_shares) + sign(self.output.target_shares)) == 0
        self.output['shorts_involved'] = self.output.curr_negative | self.output.target_negative

        def f(shorts_involved, dir_long, dir_short, reversal, direction, platform):
            if reversal:
                if direction == 'BUY':
                    return DIRECTION_CODES[platform]['short']['BUY']
                else:
                    return DIRECTION_CODES[platform]['long']['SELL']
            else:
                return (dir_short if shorts_involved else dir_long)
        self.output['first_leg'] = vectorize(f)(self.output.shorts_involved, self.output.dir_adj_long, self.output.dir_adj_short, \
            self.output.reversal, self.output.direction, self.output.trading_platform)

        def f(reversal, direction, platform):
            if reversal:
                if direction == 'BUY':
                    return DIRECTION_CODES[platform]['long']['BUY']
                else:
                    return DIRECTION_CODES[platform]['short']['SELL']
            else:
                return '-'
        self.output['second_leg'] = vectorize(f)(self.output.reversal, self.output.direction, self.output.trading_platform)
        self.output['amount_1st_leg'] = 0
        self.output.loc[~self.output.reversal, 'amount_1st_leg'] = abs(self.output.loc[~self.output.reversal, 'amount'])
        self.output.loc[self.output.reversal, 'amount_1st_leg'] = abs(self.output.loc[self.output.reversal, 'actual_shares'])
        self.output['amount_2nd_leg'] = v_int(abs(self.output.amount)) - self.output.amount_1st_leg

    def fill_LL_caps(self):
        # instead of computing on the strategy level, now takes hard-coded value from strat. sheet (one that's computed by G6 to account for all strategies)
        def f(l1, l2, c):
            if l1 + l2 <= c:
                return(l1, l2)
            elif l1 <= c:
                return(l1, c - l1)
            else:
                return(c, 0)
        vv = vectorize(f)(self.output.amount_1st_leg, self.output.amount_2nd_leg, self.output.LL_capped_qty)
        self.output['amount_1st_leg_LL_on'] = vv[0]
        self.output['amount_2nd_leg_LL_on'] = vv[1]

    def fold_flips_to_new_rows(self):
        # make separate rows out of 2nd legs of reversals; nothing happens if there are none
        reversals = self.output[self.output.amount_2nd_leg != 0].copy()
        reversals.loc[:, ['first_leg', 'amount_1st_leg', 'amount_1st_leg_LL_on']] = reversals[['second_leg', 'amount_2nd_leg', 'amount_2nd_leg_LL_on']].values
        self.output = self.output.append(reversals, ignore_index=True)
        self.output.amount_1st_leg = v_int(self.output.amount_1st_leg)
        self.output.amount_1st_leg_LL_on = v_int(self.output.amount_1st_leg_LL_on)
        self.output = self.output.sort_values(by = ['ticker', 'strategy'])
        # after columns related to 2nd legs are convereted, remove them
        # delete 'direction' column (one read from Excel), because amount_1st_leg will replace it
        self.output = self.output.drop(['second_leg', 'amount_2nd_leg', 'amount_2nd_leg_LL_on', 'direction'], axis = 1)

    def add_human_readable_direction(self):
        self.output['direction_human'] = [DIRECTION_CODES_REVERSE[x] for x in self.output.first_leg.values]

    # -----------------------------------------HELPER FUNCTIONS FOR consolidate_strategies()

    def add_consolidation_tags(self):
        multiple_trades = []
        # add columun with how many times this ticker occurs in entire table
        self.output['ticker_occurences'] = [sum(self.output.ticker == i) for i in self.output.ticker]
        # identify rows with tickers which occur more than once
        self.output['ticker_more_than_once'] = [True if i > 1 else False for i in self.output.ticker_occurences]
        for i in list(self.output.index[self.output.ticker_more_than_once]):
            ids_this_ticker = list(self.output.index[self.output.ticker == self.output.ticker[i]])
            # count only those where same ticker occurs in more than one strategy
            if len(set(self.output.loc[ids_this_ticker, :].strategy)) > 1:
                multiple_trades.append(tuple(ids_this_ticker))
        # list of lists where every element is an index
        multiple_trades = sorted([list(i) for i in list(set(multiple_trades))])

        self.output['cons_type'] = 'no'
        self.output['cons_id'] = -1
        consolidation_ID = 1

        for i in multiple_trades:
            subset = self.output.loc[i, :]
            # consolidate all orders of same type, regardless of whether or not they are a part of flip trade
            # instead of calling hardcoded case, have a general expression that works on ony number of strategies
            # even within `subset`, consolidation tag will be applied only to rows with same order - not to all rows
            repeating_order_types = list(set([i for i in list(subset.direction_human) if list(subset.direction_human).count(i) > 1]))
            for j in repeating_order_types:
                ids = subset.index[subset.direction_human == j]
                self.output.loc[ids, 'cons_type'] = 'J'
                self.output.loc[ids, 'cons_id'] = consolidation_ID
                consolidation_ID += 1

    def consolidate_order_rows(self, components):
        total_qty = sum(components.amount_1st_leg)
        total_qty_LL_on = sum(components.amount_1st_leg_LL_on)
        result = components.iloc[[0]].copy()
        result.amount_1st_leg = total_qty
        result.amount_1st_leg_LL_on = total_qty_LL_on

        # dictionary with all strategies as keys, `amount_1st_leg` if strategy in `components` and 0 otherwise
        qty_by_strategy = {i:int(components.loc[components.strategy == i, 'amount_1st_leg']) if i in list(components.strategy) else 0 for i in list(STRATEGY_CODES)[:-1]}
        result.alloc_strat_1 = round(float(qty_by_strategy['strat_1'] / total_qty), 2)
        result.alloc_strat_2 = round(float(qty_by_strategy['strat_2'] / total_qty), 2)
        result.alloc_strat_3 = round(float(qty_by_strategy['strat_3'] / total_qty), 2)
        result.alloc_strat_1_joint = round(float(qty_by_strategy['strat_1_joint'] / total_qty), 2)
        result.alloc_strat_2_joint = round(float(qty_by_strategy['strat_2_joint'] / total_qty), 2)
        result.alloc_strat_3_joint = round(float(qty_by_strategy['strat_3_joint'] / total_qty), 2)
        result.alloc_Dual = round(float(qty_by_strategy['dual'] / total_qty), 2)
        result.alloc_strat_4 = round(float(qty_by_strategy['strat_4'] / total_qty), 2)

        result.combo_schema = True
        result.strategy = 'consolidated'
        return result

    def apply_consolidation_rules(self, subset):
        # given a subset with component trades and rule, sends back ONE ROW with concolidated trades, doesn't do anything in master table
        rule = set(subset.cons_type)
        if len(set(subset.cons_type)) > 1:
            UI.error_exit('Something is wrong with your ' + str(list(set(subset.ticker))) + ' orders; check them and try again; exiting from `apply_consolidation_rules` line 149')
        rule = list(rule)[0]
        subset = subset.sort_values(by = ['first_leg', 'strategy'])

        if rule == 'J':
            result = self.consolidate_order_rows(subset)
            result.cons_type = 'done-J'
        else:
            UI.error_exit('Something is wrong with your orders for ' + str(subset.ticker))
        result.send_to_sheet = False
        return result
    # -------------------------------------END HELPER FUNCTIONS FOR consolidate_strategies()
    def consolidate_strategies(self):
        self.output['send_to_roster'] = True
        self.output['send_to_sheet'] = True
        self.output['full_size'] = 'n/a'
        self.output['combo_schema'] = False
        self.output['alloc_strat_2'] = -1.0
        self.output['alloc_strat_1'] = -1.0
        self.output['alloc_strat_3'] = -1.0
        self.output['alloc_strat_1_joint'] = -1.0
        self.output['alloc_strat_2_joint'] = -1.0
        self.output['alloc_strat_3_joint'] = -1.0
        self.output['alloc_strat_4'] = -1.0
        self.output['alloc_Dual'] = -1.0
        if self.consolid_toggle == '1':
            self.add_consolidation_tags()
            ids_to_consolidate = set(list(self.output.cons_id)) - {-1}
            for i in ids_to_consolidate:
                row_ids = self.output.index[self.output.cons_id == i]
                addition = self.apply_consolidation_rules(self.output.loc[row_ids])
                # change index of addition so there is no conflict/overwrite on append
                addition.index = [max(self.output.index) + i for i in range(1, addition.shape[0] + 1)]
                self.output = self.output.append(addition, ignore_index = False)
                self.output.loc[row_ids, 'send_to_roster'] = False

            ids = self.output.index[self.output.strategy == 'consolidated']
            columns_to_overwrite = [...]
            self.output.loc[ids, columns_to_overwrite] = 0
        else:
            # if we don't have this column then final_cleanup will freak out (warning about calling non-existent columns)
            self.output['cons_type'] = self.output['cons_id'] = 'n/a'

    def add_portfolio_mapping_columns(self):
        temp_map = match(list(self.output.ticker), list(PORTFOLIO_MAPPING.fs_ticker))
        missing = [i for (i,v) in enumerate(temp_map) if v == None]
        if len(missing) > 0:
            print('  >>  Tickers not found in `portfolio_mapping`: ', list(self.output['ticker'].values[missing]))
            input('Hit Enter to exit, then fix the `portfolio_mapping` file')
            exit()
        self.output['book'] = PORTFOLIO_MAPPING.iloc[temp_map, 2].values
        self.output['broker_ticker'] = PORTFOLIO_MAPPING.iloc[temp_map, 0].values
        self.output.loc[self.output.strategy == 'strat_4', 'book'] = 'strat_4 - unassigned'

    def add_limit_price(self):
        self.output.limit_price = vectorize(lambda i: round(i, 2))(self.output.limit_price)

    def final_cleanup(self):
        self.output = self.output.sort_values(by = ['strategy', 'book', 'ticker'])
        cols_to_keep = [...]
        self.output = self.output.loc[:, cols_to_keep]
        self.output.rename(columns={'first_leg' : 'direction', 'amount_1st_leg' : 'quantity', 'amount_1st_leg_LL_on' : 'qty_LL_on'}, inplace=True)

    def execute(self):
        self.exit_if_no_trades()
        self.add_trading_platform()
        self.fill_adj_direction()
        self.compute_flips()
        self.fill_LL_caps()
        self.fold_flips_to_new_rows()
        self.add_human_readable_direction()
        self.consolid_toggle = UI.get_multiple_choice_input('Trades between strategies will be consolidated. Hit Enter to confirm, or enter your choice (1 for Yes, 0 for No)  >>   ', ['1', '0'], '1')
        self.consolidate_strategies()
        self.add_portfolio_mapping_columns()
        self.add_limit_price()
        self.final_cleanup()

        return self.output
