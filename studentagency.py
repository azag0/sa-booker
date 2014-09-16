# coding=utf-8
import re, yaml, os
from splinter import Browser
import smtplib
from email.mime.text import MIMEText
import base64
import time
import logging

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
    def search(self, city_from, city_to, date, date_return=None, is_open=False):
        self.browser.find_by_id('hp_form_itinerar').first \
                    .find_by_xpath('div/input[@type="radio"]'
                                   )[1 if date_return or is_open else 0].check()
        for city, i in [(city_from, 1), (city_to, 2)]:
            self.browser.find_by_css('input[tabindex="{}"]'.format(i)) \
                        .first.fill(city)
            for item in self.browser.find_by_css('.ui-menu-item'):
                link = item.find_by_tag('a')
                if link.value.lower() == city.lower():
                    link.click()
                    break
        self.browser.fill('departure:dateField', date)
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
        time_table = []
        for item in items:
            if item.tag_name == 'h2':
                date = item.text.split(' ')[1]
            elif item.tag_name == 'div' and item.has_class('routeSummary'):
                assert date
                if date != date:
                    break
                info = [c.value for c in item.find_by_xpath('div') if c.value]
                bus_type = item.find_by_css('.col_icons2').first \
                               .find_by_xpath('a/img')
                if not bus_type:
                    bus_type = 'standard'
                else:
                    bus_type = bus_type.first._element.get_attribute("alt")
                    if 'Fun a Relax' in bus_type:
                        bus_type = 'fun&relax'
                    elif 'Ekonomy standard' in bus_type:
                        bus_type = 'posila'
                if int(info[3]):
                    time_table.append((info[0], bus_type, item.find_by_css('.col_price')))
        return time_table
    def order_time(self, connection):
        while True:
            connection.click()
            dialog = self.browser.find_by_css('[id^=_wicket_window]')
            if dialog:
                dialog.first.find_by_tag('button').click()
            if self.browser.is_element_present_by_id('sumary_lines', wait_time=1):
                break
        self.browser.find_by_id('sumary_lines') \
                    .first.find_by_tag('button') \
                    .first.click()
        seats = {}
        bus = self.browser.find_by_css('.seatsContainer')
        if bus:
            for seat in bus.first.find_by_xpath('div[@class="seatContainer"]'):
                seats[int(seat.find_by_tag('div').first.html[:-1])] = seat
        else:
            raise Exception()
        return seats
    def order_seat(self, seat):
        seat.click()
        submit = self.browser.find_by_css('[name^=buttonContainer]').first
        interaction_type = submit.text
        if not u'Rezervovat' in interaction_type:
            submit.click()
            data = (self.user['first'], 
                    self.user['last'], 
                    self.user['email'], 
                    self.user['phone'])
            for item, value in zip(self.browser.find_by_id('passengerInfo') \
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
            while self.browser.is_element_not_present_by_id('ticketPage', wait_time=1):
                pass
            msg = MIMEText(self.browser.find_by_id('ticketPage') \
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

