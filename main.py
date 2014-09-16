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
      log.info('Loaded users: ' + ', '.join(users.keys()))
      with open('data.yaml') as f:
         tasks = [sa.Task(t) for t in yaml.load(f)]
      log.info('Loaded tasks:')
      for t in tasks:
         log.info(t)
      sessions = {}
      while True:
         for task in tasks:
            try:
               if not task.account in sessions:
                  sessions[task.account] = sa.Session(args['--browser'],
                                                      users[task.account])
                  log.info('Session for account {} created'.format(task.account))
               s = sessions[task.account]
               connections = s.search(task)
               for conn in connections:
                   if conn.is_free() and task.match_connection(conn):
                      seats = s.order_time(conn)
                      s.order_seat(seats.popitem()[1])
                      s.go_search()
                      task.finished = True
                      now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                      log.info('Booked! Time: {}'.format(now))
                      log.info(task)
            except: 
                pass
         tasks = [t for t in tasks if not t.finished]
         if not tasks:
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
