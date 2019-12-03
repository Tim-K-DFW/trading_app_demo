from codes_joint import *
from sys import exit

def greeting():
    save_confirmation = input('Have you refreshed and saved all the books? (type "yes" if you have) >> ')
    if save_confirmation != 'yes':
        print('That was a wrong answer.')
        input('Hit Enter to exit')            
        exit()
    else:
        save_confirmation2 = input('ARE YOU SURE??? (type "I am" if you are sure) >> ')
        if save_confirmation2 != 'I am':
            input('Hit Enter to exit')
            exit()

    reconcile_confirmation = input('Have you RECONCILED all the books? (type "YES" if you have) >> ')
    if reconcile_confirmation != 'YES':
        print('How can you trade if you don\'t even know what your positions are?')
        input('Hit Enter to exit')            
        exit()
    else:
        reconcile_confirmation2 = input('Look, you think you have reconciled, but what if you haven\'t? ARE YOU SURE? (type "Reconciled" if you are sure) >> ')
        if reconcile_confirmation2 != 'Reconciled':
            input('Hit Enter to exit')
            exit()

# temporary, for beta testing
def beta_warning():
    print('THIS IS A BETA VERSION')
    print('Try to mess with it as much as you can, provide bad input, etc., so we can catch all errors now and not later.')
    print('all trades generated will be be in "---temp - development\\---Batch Trade Submission - test"')
    input('Hit Enter to continue')

def get_params():
    save_confirmation = input('Have you refreshed and saved all the books? (type "yes" if you have) >> ')
    if save_confirmation != 'yes':
        print('Well then do that first...')
        input('Hit Enter to exit')            
        exit()
    else:
        save_confirmation2 = input('ARE YOU SURE??? (type "I am" if you are sure) >> ')
        if save_confirmation2 != 'I am':
            input('Hit Enter to exit')
            exit()

    reconcile_confirmation = input('Have you RECONCILED all the books? (type "YES" if you have) >> ')
    if reconcile_confirmation != 'YES':
        print('How can you trade if you don\'t even know what your positions are?')
        input('Hit Enter to exit')            
        exit()
    else:
        reconcile_confirmation2 = input('Look, you think you have reconciled, but what if you haven\'t? ARE YOU SURE? (type "Reconciled" if you are sure) >> ')
        if reconcile_confirmation2 != 'Reconciled':
            input('Hit Enter to exit')
            exit()

def error_exit(message):
    print(message)
    input('Hit Enter to exit')
    exit()

def get_multiple_choice_input(message, options, default = '--none'):
    result = default
    while True:
        attempt = input(message)
        if attempt == '' and default != '--none':
            break
        elif attempt in options:
            result = attempt
            break
        else:
            print('''
                Invalid input, bro. Try again.''')
    return result

def invalid_tickers(attempt):
    return list(set(attempt) - set(PORTFOLIO_MAPPING.fs_ticker))

def get_ticker_list(message, blank_allowed = False):
    while True:
        confirm = input(message).split()
        if len(confirm) == 0:

            if blank_allowed:
                result = []
                break
            else:
                print('You have to select at least one ticker.')
        else:
            if len(invalid_tickers(confirm)) == 0 or confirm == ['--ALL']:
                result = confirm
                break
            else:
                print('You\'ve entered some invalid tickers, bro: ' + str(invalid_tickers(confirm)) + '. Try again.')
    return result


def show_done_message():
    print('\n\n\n  >>  Make sure to double-check your trades.\n\n\n')
    input('  >>  Hit Enter to exit')
