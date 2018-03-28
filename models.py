# -*- coding: utf-8 -*-

import re
import datetime

class ResultSet(list):
    """A list like object that holds results from a RTM API query."""

class ModelBase(object):
    """Base model class"""

    def __init__(self):
        """Setup default datas."""
        pass

    def __repr__(self):
        return u'<%s - %s>' % (self.__class__.__name__, 
                u', '.join([c for c in dir(self) if not c.startswith(u'_')]))

    def __getstate__(self):
        return dict(self.__dict__)

    @classmethod
    def _parse(cls, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def _parse_list(cls, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        if not json_list:
            return ResultSet()

        if type(json_list) is not list:
            json_list = [json_list, ]
        return ResultSet(cls._parse(obj) for obj in json_list if obj)

class Frob(ModelBase):
    @classmethod
    def _parse(cls, json):
        return json[u'frob']

class Stat(ModelBase):
    @classmethod
    def _parse(cls, json):
        if json[u'stat'] == u'ok':
            return True
        return False

class Timeline(ModelBase):
    @classmethod
    def _parse(cls, json):
        return json[u'timeline']

class User(ModelBase):
    @classmethod
    def _parse(cls, json):
        user = cls()
        for k, v in json[u'user'].items():
            if k in [u'id', ]:
                setattr(user, k, int(v))
            else:
                setattr(user, k, v and v or None)
        return user

class Auth(ModelBase):
    @classmethod
    def _parse(cls, json):
        auth = cls()
        for k, v in json[u'auth'].items():
            if k == u'user':
                user = User._parse(json[u'auth'])
                setattr(auth, k, user)
            else:
                setattr(auth, k, v and v or None)
        return auth

class List(ModelBase):
    @classmethod
    def _parse(cls, json):

        # for rtm.lists.add, archive, delete, setName, unarchive
        if list in json:
            json = json['list']

        _list = cls()
        for k, v in json.items():
            if k in [u'locked', u'archived', u'deleted', u'smart', ]:
                setattr(_list, k, v==u'1' and True or False)
            elif k in [u'id', u'sort_order', u'position', ]:
                setattr(_list, k, int(v))
            else:
                setattr(_list, k, v and v or None)
        return _list

class Lists(ModelBase):
    @classmethod
    def _parse(cls, json):
        if not json['lists'] or not json['lists']['list']:
            return ResultSet()
        return List._parse_list(json['lists']['list'])

# For task recurrences
RE_FREQ = re.compile(r"FREQ=(?P<freq>[a-z]+)", re.I)
RE_INTERVAL = re.compile(r"INTERVAL=(?P<interval>[\d]+)", re.I)
RE_WEEKLY_BYDAY = re.compile(r"BYDAY=(?P<byday>[a-z,]+)", re.I)
RE_MONTHLY_BYDAY = re.compile(r"BYDAY=(?P<byday>[-\w]+)", re.I)
RE_BYMONTHDAY = re.compile(r"BYMONTHDAY=(?P<bymonthday>[\d]+)", re.I)
RE_UNTIL = re.compile(r"UNTIL=(?P<until>[\w]+)", re.I)
RE_COUNT = re.compile(r"COUNT=(?P<count>[\d]+)", re.I)

class Recurrence(ModelBase):
    def __init__(self):
        super(Recurrence, self).__init__()
        self.freq = None
        self.interval = None
        self.byday = None
        self.bymonthday = None
        self.until = None
        self.count = None

    @classmethod
    def _parse(cls, json):
        recurrence = cls()

        for k, v in json.items():
            if k == u'$t':
                m = RE_FREQ.search(v)
                if m:
                    recurrence.freq = m.group('freq').upper()

                m = RE_INTERVAL.search(v)
                if m:
                    recurrence.interval = m.group('interval') and int(m.group('interval')) or None

                m = RE_WEEKLY_BYDAY.search(v)
                if m:
                    recurrence.byday = m.group('byday').upper().split(u',')

                m = RE_MONTHLY_BYDAY.search(v)
                if m:
                    recurrence.byday = m.group('byday').upper()

                m = RE_BYMONTHDAY.search(v)
                if m:
                    recurrence.bymonthday = m.group('bymonthday') and int(m.group('bymonthday')) or None

                m = RE_UNTIL.search(v)
                if m:
                    recurrence.until = m.group('until') and datetime.datetime.strptime(
                            v.upper(), "%Y%m%dT%H%M%SZ")

                m = RE_COUNT.search(v)
                if m:
                    recurrence.count = m.group('count') and int(m.group('count')) or None
            elif k in [u'every', ]:
                setattr(recurrence, k, v and int(v) or None)
            else:
                setattr(recurrence, k, v)

        return recurrence

# For task estimates
RE_DAYS = re.compile(r"(?P<days>[\d.]+)\s*d", re.I)
RE_HOURS = re.compile(r"(?P<hours>[\d.]+)\s*h", re.I)
RE_MINUTES = re.compile(r"(?P<minutes>[\d.]+)\s*m", re.I)

class Task(ModelBase):
    @classmethod
    def _parse(cls, json):
        task = cls()

        for k, v in json.items():
            if k == u'priority':
                if v == u'N':
                    setattr(task, k, None)
                else:
                    setattr(task, k, v and int(v) or None)
            elif k in [u'has_due_time', ]:
                setattr(task, k, v==u'1' and True or False)
            elif k in [u'added', u'completed', u'deleted', u'due']:
                setattr(task, k, v and datetime.datetime.strptime(
                    v, '%Y-%m-%dT%H:%M:%SZ') or None)
            elif k in [u'postponed', ]:
                setattr(task, k, int(v))
            elif k in [u'estimate', ]:
                estimate = None
                if v:
                    days = 0.0
                    hours = 0.0
                    minutes = 0.0

                    m = RE_DAYS.search(v)
                    if m:
                        days = float(m.group('days'))
                    m = RE_HOURS.search(v)
                    if m:
                        hours = float(m.group('hours'))
                    m = RE_MINUTES.search(v)
                    if m:
                        minutes = float(m.group('minutes'))
                    if days or hours or minutes:
                        estimate = datetime.timedelta(days=days, hours=hours, minutes=minutes)

                setattr(task, k, estimate)
            else:
                setattr(task, k, v and v or None)

        return task

class Note(ModelBase):
    @classmethod
    def _parse(cls, json):
        note = cls()

        # for rtm.tasks.notes.add, edit
        if 'note' in json:
            json = json[u'note']

        for k, v in json.items():
            if k == u'$t':
                setattr(note, u'text', v)
            elif k in [u'id', ]:
                setattr(note, k, int(v))
            else:
                setattr(note, k, v and v or None)
        return note

class TaskSeries(ModelBase):
    def __init__(self):
        super(TaskSeries, self).__init__()
        self.task = ResultSet()
        self.rrule = None
        self.tags = ResultSet()
        self.notes = ResultSet()
        self.participants = ResultSet()

    @classmethod
    def _parse(cls, json):
        taskseries = cls()

        for k, v in json.items():
            if k == u'task':
                taskseries.task = Task._parse_list(v)
            elif k == u'rrule':
                taskseries.rrule = Recurrence._parse(v)
            elif k == u'tags':
                if v and 'tag' in v:
                    if type(v[u'tag']) is list:
                        taskseries.tags = v[u'tag']
                    else:
                        taskseries.tags = ResultSet(v[u'tag'], )
            elif k == u'notes':
                if v and 'note' in v:
                    taskseries.notes = Note._parse_list(v[u'note'])
            elif k == u'participants':
                if v and 'contact' in v:
                    taskseries.participants = Contact._parse_list(v[u'contact'])
            elif k in [u'created', u'modified', ]:
                setattr(taskseries, k, v and datetime.datetime.strptime(
                    v, '%Y-%m-%dT%H:%M:%SZ') or None)
            elif k in [u'location_id', ]:
                setattr(taskseries, k, v and int(v) or None)
            else:
                setattr(taskseries, k, v and v or None)
        return taskseries

class TaskList(ModelBase):
    def __init__(self):
        super(TaskList, self).__init__()
        self.taskseries = ResultSet()

    @classmethod
    def _parse(cls, json):
        _list = cls()

        # for rtm.tasks.add
        if 'list' in json:
            json = json['list']

        for k, v in json.items():
            if k == 'taskseries':
                _list.taskseries = TaskSeries._parse_list(v)
            elif k in ['id', ]:
                setattr(_list, k, int(v))
            else:
                setattr(_list, k, v and v or None)
        return _list

class Tasks(ModelBase):
    def __init__(self):
        super(Tasks, self).__init__()
        self.lists = ResultSet()

    @classmethod
    def _parse(cls, json):
        tasks = cls()

        for k, v in json[u'tasks'].items():
            if k == u'list':
                tasks.lists = TaskList._parse_list(v)
            else:
                setattr(tasks, k, v and v or None)
        return tasks

class Contact(ModelBase):
    @classmethod
    def _parse(cls, json):
        contact = cls()

        # for rtm.contacts.delete
        if 'contact' in json:
            json = json[u'contact']

        for k, v in json.items():
            if k in [u'id', ]:
                setattr(contact, k, int(v))
            else:
                setattr(contact, k, v and v or None)
        return contact

class Contacts(ModelBase):
    @classmethod
    def _parse(cls, json):
        if not json[u'contacts'] or not 'contact' in json[u'contacts']:
            return ResultSet()
        return Contact._parse_list(json[u'contacts'][u'contact']);

class Group(ModelBase):
    def __init__(self):
        super(Group, self).__init__()
        self.contacts = ResultSet()

    @classmethod
    def _parse(cls, json):
        group = cls()

        # for rtm.group.delete
        if 'group' in json:
            json = json[u'group']

        for k, v in json.items():
            if k == u'contacts':
                group.contacts = Contacts._parse(json)
            elif k in [u'id', ]:
                setattr(group, k, int(v))
            else:
                setattr(group, k, v and v or None)
        return group

class Groups(ModelBase):
    @classmethod
    def _parse(cls, json):
        if not json[u'groups'] or not 'group' in json[u'groups']:
            return ResultSet()
        return Group._parse_list(json[u'groups'][u'group']);

class Argument(ModelBase):
    @classmethod
    def _parse(cls, json):
        argument = cls()
        for k, v in json.items():
            if k == u'$t':
                setattr(argument, u'description', v)
            elif k in [u'optional', ]:
                setattr(argument, k, v==u'1' and True or False)
            else:
                setattr(argument, k, v and v or None)
        return argument

class Error(ModelBase):
    @classmethod
    def _parse(cls, json):
        error = cls()
        for k, v in json.items():
            if k == u'$t':
                setattr(error, u'description', v and v or None)
            elif k in [u'code', ]:
                setattr(error, k, int(v))
            else:
                setattr(error, k, v and v or None)
        return error

class Method(ModelBase):
    def __init__(self):
        super(Method, self).__init__()
        self.arguments = ResultSet()
        self.errors = ResultSet()

    @classmethod
    def _parse(cls, json):
        method = cls()

        for k, v in json[u'method'].items():
            if k == u'arguments' and 'argument' in v:
                method.arguments = Argument._parse_list(v[u'argument'])
            elif k == u'errors' and 'error' in v:
                method.errors = Error._parse_list(v[u'error'])
            elif k in [u'needslogin', u'needssigning', u'requiredperms', ]:
                setattr(method, k, v==u'1' and True or False)
            else:
                setattr(method, k, v and v or None)
        return method

class Methods(ModelBase):
    @classmethod
    def _parse(cls, json):
        return json[u'methods'][u'method']

class Timezone(ModelBase):
    @classmethod
    def _parse(cls, json):
        timezone = cls()
        for k, v in json.items():
            if k in [u'id', u'dst', u'offset', u'current_offset',]:
                setattr(timezone, k, int(v))
            else:
                setattr(timezone, k, v and v or None)
        return timezone

class Timezones(ModelBase):
    @classmethod
    def _parse(cls, json):
        return Timezone._parse_list(json[u'timezones'][u'timezone']);

class Time(ModelBase):
    @classmethod
    def _parse(cls, json):
        time = cls()
        for k, v in json[u'time'].items():
            if k == u'$t':
                setattr(time, u'time', v and v or None)
            else:
                setattr(time, k, v and v or None)
        return time

class Location(ModelBase):
    @classmethod
    def _parse(cls, json):
        location = cls()
        for k, v in json.items():
            if k in [u'viewable', ]:
                setattr(location, k, v==u'1' and True or False)
            elif k in [u'id', u'zoom', ]:
                setattr(location, k, int(v))
            elif k in [u'longitude', u'latitude', ]:
                setattr(location, k, v and float(v) or None)
            else:
                setattr(location, k, v and v or None)
        return location

class Locations(ModelBase):
    @classmethod
    def _parse(cls, json):
        if not json[u'locations'] or not 'location' in json['locations']:
            return ResultSet()
        return Location._parse_list(json[u'locations'][u'location'])

class Settings(ModelBase):
    @classmethod
    def _parse(cls, json):
        settings = cls()
        for k, v in json[u'settings'].items():
            if k in [u'defaultlist', u'dateformat', u'timeformat', ]:
                setattr(settings, k, int(v))
            else:
                setattr(settings, k, v and v or None)
        return settings

