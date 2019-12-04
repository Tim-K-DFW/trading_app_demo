# Trade aggregator
*All code fully preserved; several inconsequential string literals were redacted or replaced.*

#### Business case

I developed this app when working for an investment fund which managed several systematic long-short equity strategies. Every strategy was a separate entity (outside of this app) that produced a list of current and target positions. The app consolidated such lists from multiple files and converted them into a bundle of batch trade file for prime brokers and reports for the investment team.

All portfolios of this fund, with combined value in the nine digits, were traded through this app, 600-700 trades per batch during normal days and up to 1,500 trades during peak seasons, with 1-2 batches daily.

For full disclosure, this was a side project for me, since my full-time job was on the investment side, in generation and evaluation of investment strategies. However, as the number of strategies and their scope increased, we had to automate most of the trading, hence this app.

This app was built for in-house use as part of specific pipeline, and as such has no utility outside of its native stack. Now that the fund is shut down, I publish this sterilized version purely for coding demonstration purposes.

#### Key features

- text-based interface that allowed user to choose order type, strategy and ticker subsets and other parameters
- several order types depending on execution objective (limit, market, market on close)
- order consolidation with elaborate rules to minimize market impact and trading costs, i.e. proper handling of various permutations of different orders from different strategies acting on the same stock (long vs short, partial vs full, closing vs opening etc.), while ensuring compliance with broker API and internal trade accounting rules
- proper treatment of "crossing zero" (e.g. when switching from long to short position in one trade requires separate long sell and then short sell orders)
- multiple defensive checks and user prompts throughout the process to minimize human error and maintain data integrity.

#### Design and code highlights

- highly modular structure allowing easy and error-free addition and modification of strategies, user interface and processing rules, as well as subsequent seamless merge with the portfolio management app that we were building
- minimal use of `for` loops, full vectorization of column-wise dataframe operations
- exquisite use of `pandas`'s reshaping and multilevel indexing (`TradeSummaryWriter` class)
- fully "plug-and-play" treatment of report columns (string literals). I.e. different strategies needed different information presented in report files (up to 10 different columns per strategy), and instead of hard-coding each set of column names, I factored them out to a `yaml` file, such that changes could be made without altering core code
- was shipped as a single `exe` file which ran on any Windows machine
- maintained full test coverage up to two strategies, had to suspend it due to time constraints.
