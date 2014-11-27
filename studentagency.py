# coding=utf-8
import re
import yaml
import os
from splinter import Browser
import smtplib
from email.mime.text import MIMEText
import base64
import time
import logging


class Task:
    def __init__(self, data):
        self.account = data['account']
        self.from_city = data['from']
        self.to_city = data['to']
        self.date = data['date']
        self.time = data['time']
        self.posila = 'posila' not in data or data['posila']
        self.finished = False

    def __str__(self):
        return u'account: {}, from: {}, to: {}, date: {}, time: {}, ' \
               u'posila: {}'.format(self.account, self.from_city,
                                    self.to_city, self.date,
                                    self.time, self.posila)

    def match_connection(self, conn):
        return self.time == conn.departure and \
            (conn.type != 'posila' or self.posila)


class Connection:
    def __init__(self, html_elem):
        info = [c.value for c in html_elem.find_by_xpath('div') if c.value]
        self.departure = info[0]
        self.arrival = info[1]
        self._free = 0 if info[3] == "-" else int(info[3])
        self.price = re.match(r'(.*) CZK', info[4]).group(1) \
            if self.is_free() else None
        icons = html_elem.find_by_css('.col_icons2').first \
                         .find_by_xpath('a/img')
        if not icons:
            self.type = 'standard'
        else:
            alt_text = icons.first._element.get_attribute("alt")
            if 'Fun a Relax' in alt_text:
                self.type = 'fun&relax'
            elif 'Ekonomy standard' in alt_text:
                self.type = 'posila'
            else:
                self.type = None
                log = logging.getLogger(__name__)
                log.warning('Unknown bus type:')
                log.warning(alt_text)
        self._button = html_elem.find_by_css('.col_price')

    def is_free(self):
        return self._free > 0

    def click(self):
        self._button.click()


class Session:
    def __init__(self, browser, user):
        self.browser = Browser(browser)
        self.browser.visit('http://jizdenky.studentagency.cz/')
        self.browser.fill_form({'passwordAccountCode': user['login'],
                                'password': user['password']})
        self.browser.find_by_value(u'Přihlásit').first.click()
        self.user = user
        self.log = logging.getLogger(__name__)

    def go_search(self):
        self.browser.find_by_id('user_box_menu') \
            .find_by_xpath('table/tbody/tr/td/a').click()

    def search(self, task, date_return=None, is_open=False):
        self.browser.find_by_id('hp_form_itinerar').first \
            .find_by_xpath('div/input[@type="radio"]'
                           )[1 if date_return or is_open else 0].check()
        for city, i in [(task.from_city, 1), (task.to_city, 2)]:
            self.browser.find_by_css('input[tabindex="{}"]'.format(i)) \
                        .first.fill(city)
            for item in self.browser.find_by_css('.ui-menu-item'):
                link = item.find_by_tag('a')
                if link.value.lower() == city.lower():
                    link.click()
                    break
        self.browser.fill('departure:dateField', task.date)
        if date_return:
            self.browser.fill('returnDeparture:dateField', date_return)
        if is_open:
            self.browser.check('returnTicketOpen')
        self.browser.find_option_by_text(u'Isic/Alive').first.check()
        self.browser.find_by_value('Vyhledat').first.click()
        while self.browser.is_element_not_present_by_css('.left_column',
                                                         wait_time=1):
            pass
        items = self.browser.find_by_css('.left_column') \
                            .find_by_xpath('div/div/*')
        connections = []
        for item in items:
            if item.tag_name == 'h2':
                date_local = item.text.split(' ')[1]
            elif item.tag_name == 'div' and item.has_class('routeSummary'):
                assert date_local
                if date_local != task.date:
                    break
                connections.append(Connection(item))
        return connections

    def order_time(self, connection):
        while True:
            connection.click()
            dialog = self.browser.find_by_css('[id^=_wicket_window]')
            if dialog:
                dialog.first.find_by_tag('button').click()
            if self.browser.is_element_present_by_id('sumary_lines',
                                                     wait_time=1):
                break
        self.browser.find_by_id('sumary_lines') \
                    .first.find_by_tag('button') \
                    .first.click()
        seats = {}
        bus = self.browser.find_by_css('.seatsContainer')
        if bus:
            for seat in bus.first.find_by_css(
                    '.seatContainer:not([style*=blocked])'):
                seats[int(seat.find_by_tag('div').first.html[:-1])] = seat
        else:
            bus = self.browser.find_by_css('.vehicle')
            for seat in bus.first.find_by_css('.free, .selected'):
                seats[int(seat.text[:-1])] = seat
        return seats

    def order_seat(self, seat):
        if not seat.has_class('selected'):
            seat.click()
        submit = self.browser.find_by_css('[name^=buttonContainer]').first
        interaction_type = submit.text
        if not u'Rezervovat' in interaction_type:
            submit.click()
            data = (self.user['first'], 
                    self.user['last'], 
                    self.user['email'], 
                    self.user['phone'])
            for item, value in zip(self.browser.find_by_id('passengerInfo')
                                               .first.find_by_tag('input'),
                                   data):
                item.fill(value)
            submit = self.browser.find_by_css('[name^=buttonContainer]').first
            interaction_type = submit.text
        assert u'Rezervovat' in interaction_type
        time.sleep(1)
        submit.click()
        if os.path.exists('email.yaml'):
            with open('email.yaml') as f:
                email = yaml.load(f)
            while self.browser.is_element_not_present_by_id('ticketPage',
                                                            wait_time=1):
                pass
            msg = MIMEText(self.browser.find_by_id('ticketPage')
                                       .first.html.encode('utf-8'),
                           'html')
            msg['Subject'] = 'SA reservation'
            msg['From'] = email['from']
            msg['To'] = self.user['email']
            username = email['username']
            password = email['password']
            server = smtplib.SMTP(email['server'])
            server.starttls()
            server.login(username, base64.b64decode(password))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
