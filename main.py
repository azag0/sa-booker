'''Automatically checks for free seats in Student Agency buses and books
the required tickets if available.

Usage:
    main.py [--browser=BROWSER]
    main.py (-h | --help)

Options:
    -h --help                 show this help
    --browser=BROWSER         use this browser [default: firefox]
'''
import os, sys, time, datetime, yaml
import logging
import docopt
from schema import Schema, And, Or, Use, SchemaError
import studentagency as sa

def main(args=None):
   args = docopt.docopt(__doc__, args)
   browsers = ['chrome', 'firefox']
   args_schema = Schema(
      {'--browser': And(lambda b: b in browsers,
                        error='available browsers: ' + ', '.join(browsers)),
       str: object})
   args = args_schema.validate(args) 
   logging.basicConfig(level=logging.INFO)
   log = logging.getLogger(__name__)
   try:
      with open('users.yaml') as f:
         users = yaml.load(f)
      with open('data.yaml') as f:
         zarezervuj = yaml.load(f)
      sessions = {}
      while True:
         for res in zarezervuj:
            try:
               if not res['account'] in sessions:
                  sessions[res['account']] = sa.Session(args['--browser'],
                                                         users[res['account']])
               s = sessions[res['account']]
               connections = s.search(res['from'], res['to'], res['date'])
               if res['time'] in connections:
                  seats = s.order_time(connections[res['time']])
                  s.order_seat(seats.popitem()[1])
                  del zarezervuj[zarezervuj.index(res)]
                  s.go_search()
                  log.info('Booked!')
                  log.info(yaml.dump(res, encoding='utf-8'))
            except: 
                pass
         if len(zarezervuj) == 0:
            log.info('All tickets booked, exiting')
            return 0
         time.sleep(15)
   except KeyboardInterrupt:
      log.info('Interrupted, exiting now')
      return 0
   except:
      log.exception('Unknown error')
      return 1
   finally:
      for s in sessions.values():
         s.browser.quit()

if __name__ == '__main__':
    sys.exit(main())
