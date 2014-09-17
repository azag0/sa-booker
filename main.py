'''Automatically checks for free seats in Student Agency buses and books
the required tickets if available.

Usage:
    main.py [--browser=BROWSER] [--log=LOG]
    main.py (-h | --help)

Options:
    -h --help                 show this help
    --browser=BROWSER         use this browser [default: firefox]
    --log=LOG                 use file for logging [default: error stream]
'''
import os, sys, time, datetime, yaml
import logging
import docopt
from schema import Schema, And, Or, Use, SchemaError
import studentagency as sa
import time
import signal

def main(args=None):
   args = docopt.docopt(__doc__, args)
   browsers = ['chrome', 'firefox']
   args_schema = Schema(
      {'--browser': And(lambda b: b in browsers,
                        error='available browsers: ' + ', '.join(browsers)),
       '--log': Or(And(lambda f: f == 'error stream',
                       Use(lambda x: None)),
                   str),
       str: object})
   args = args_schema.validate(args) 
   def sigterm_handler(signal, frame):
      raise KeyboardInterrupt()
   signal.signal(signal.SIGTERM, sigterm_handler)
   logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s: %(levelname)s: %(message)s',
                       filename=args['--log'],
                       datefmt='%y-%m-%d %H:%M:%S')
   log = logging.getLogger(__name__)
   log.info('Starting')
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
      log_interval = 600
      last_log_time = time.time()-log_interval
      n_tries = 0
      while True:
         if time.time()-last_log_time > log_interval:
            log.info('Alive, {} tasks in queue, {} attempts '
                     'since last log'.format(len(tasks), n_tries))
            last_log_time = time.time()
            n_tries = 0
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
                     log.info('Free connection found!')
                     log.info(task)
                     seats = s.order_time(conn)
                     log.info('Free seats: {}'.format(seats.keys()))
                     if not seats:
                        log.warn('Someone overtook you...')
                        s.go_search()
                        break
                     s.order_seat(seats.popitem()[1])
                     s.go_search()
                     task.finished = True
                     log.warning('Booked!')
                     last_log_time -= log_interval
            except: 
               raise
            n_tries += 1
         tasks = [t for t in tasks if not t.finished]
         if not tasks:
            log.info('All tickets booked, exiting')
            return 0
         time.sleep(15)
   except KeyboardInterrupt:
      log.info('Interrupted, exiting')
      return 0
   except:
      log.exception('Unknown error')
      return 1
   finally:
      for s in sessions.values():
         s.browser.quit()
      log.info('Finished')

if __name__ == '__main__':
    sys.exit(main())
