## Student Agency booker ##

This Python 3 program books requested bus tickets with Student Agency by interacting with a web browser (firefox, chrome) using the [splinter](https://github.com/cobrateam/splinter) library.

### Usage ###

Create `conf.yaml` which contains information about Student Agency accounts as in

```yaml
accounts:
  user1:
    login: <9-digit login>
    password: <password>
    phone: <phone in international format>
    email: <email>
    first: <first name>
    last: <last name>
```

The program reads information about requested tickets from standard input in the following YAML format

```yaml
- account: user1
  from: Praha
  to: Brno
  date: 24.12.2014
  time: "14:00"
```

The quotes around the time are needed.

To obtain information emails when a booking is made (optional), add the following to `conf.yaml`

```yaml
email:
  from: <sender email>
  server: smtp.gmail.com:587
  username: <smtp username>
  password: <base64 encoded smtp password>
```

See `sabooker --help`

### TODO ###

- Make it to work with [PhantomJS](http://phantomjs.org).
- Optimize speed.
- Make it a proper web app.