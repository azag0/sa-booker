## Student Agency booker ##

This python program books requested bus tickets with Student Agency by interacting with a web browser (firefox, chrome) via splinter.

### Usage ###

Create `users.yaml` which contains information about Student Agency accounts as in

```yaml
user1:
  login: <9-digit login>
  password: <password>
  phone: <phone in international format>
  email: <email>
  first: <first name>
  last: <last name>
user2:
...
```

Create `data.yaml` with the required tickets as in

```yaml
- account: user1
  from: Praha
  to: Brno
  date: 24.12.2014
  time: "14:00"
- ...
```

Mind the quotes around the time.

To obtain information emails when a booking is made (optional), create `email.yaml` as in

```yaml
from: <sender email>
server: smtp.gmail.com:587
username: <smtp username>
password: <base64 encoded smtp password>
```

Run `python main.py --help` to learn how to run the program.

### TODO ###

- Get it work with `phantomjs`
- Optimize speed?
- Make it a proper web application

