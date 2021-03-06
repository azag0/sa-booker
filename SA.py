# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import re
import yaml
from splinter import Browser
import smtplib
from email.mime.text import MIMEText
from base64 import b64decode
import time
import logging


class Task:
    def __init__(self, data):
        self.account = data['account']
        self.from_city = data['from']
        self.to_city = data['to']
        self.date = data['date']
        self.time = data['time']
        self.allow_posila = data.get('posila', True)
        self.finished = False

    def __str__(self):
        return 'account: {}, from: {}, to: {}, date: {}, time: {}, posila: {}' \
            .format(self.account, self.from_city, self.to_city, self.date,
                    self.time, self.allow_posila)

    def __contains__(self, conn):
        return self.time == conn.departure and \
            (self.allow_posila or conn.type != 'posila')


class Connection:
    def __init__(self, html_elem):
        info = [c.value for c in html_elem.find_by_xpath('div') if c.value]
        self.departure = info[0]
        self.arrival = info[1]
        self.free = int(info[3])
        if self.free:
            self.price = re.match(r'(.*) CZK', info[4]).group(1)
        else:
            self.price = None
        icons = html_elem \
            .find_by_css('.col_icons2') \
            .first \
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
            self._html_elem = html_elem

    def click(self):
        if self._html_elem.find_by_css('.col_price'):
            self._html_elem.find_by_css('.col_price').click()
        else:
            self._html_elem.find_by_css('.detailButton').click()
            self._html_elem.parent \
                .find_by_css('div[style*=block]').first \
                .find_by_css('.detail_icon').first \
                .click()


class Session:
    def __init__(self, browser, user):
        self.browser = Browser(browser)
        self.browser.visit('http://jizdenky.studentagency.cz/')
        self.browser.fill_form({'passwordAccountCode': user['login'],
                                'password': user['password']})
        self.browser.execute_script('window.scrollTo(0, 100)')
        button = self.browser.find_by_value('Přihlásit').first
        button.click()
        self.user = user
        self.log = logging.getLogger(__name__)

    def go_search(self):
        self.browser.visit('http://jizdenky.studentagency.cz/')

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
        self.browser.find_option_by_text('ISIC').first.check()
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
            if connection.click():
                self.browser

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
        for fs in self.browser.find_by_css('fieldset.topRoute'):
            legend = fs.find_by_css('legend')
            if legend and 'Pojištění' in legend[0].text:
                for package in fs.find_by_css('.insurancePackageType'):
                    if 'nechci' in package.find_by_tag('label').text:
                        package.find_by_tag('input').click()
                        time.sleep(1)
        submit = self.browser.find_by_css('[name^=buttonContainer]').first
        interaction_type = submit.text
        reserved = 'Rezervovat' in interaction_type
        if not reserved:
            submit.click()
            time.sleep(1)
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
            assert 'Rezervovat' in interaction_type
        agreement = self.browser.find_by_css('[name="bottomComponent:termsAgreementCont:termsAgreementCB"]')
        if agreement:
            agreement[0].check()
        time.sleep(1)
        submit.click()
        with open('conf.yaml') as f:
            conf = yaml.load(f)
        if 'email' in conf:
            email = conf['email']
            while self.browser.is_element_not_present_by_id('ticketPage', wait_time=1):
                pass
            msg = MIMEText(self.browser.find_by_id('ticketPage').first.html, 'html')
            msg['Subject'] = 'SA reservation'
            msg['From'] = email['from']
            msg['To'] = self.user['email']
            username = email['username']
            password = email['password']
            server = smtplib.SMTP(email['server'])
            server.starttls()
            server.login(username, b64decode(password).decode())
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
