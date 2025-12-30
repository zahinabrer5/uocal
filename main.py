import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from pathlib import Path
from zoneinfo import ZoneInfo

if (args_count := len(sys.argv)) > 2:
    print(f'1 argument expected, got {args_count - 1}')
    raise SystemExit(2)
elif args_count < 2:
    print('You must specify the target file')
    raise SystemExit(2)

file = Path(sys.argv[1])

if not file.is_file():
    print('The file does not exist')
    raise SystemExit(1)

with open(file, 'r') as f:
    soup = BeautifulSoup(f, 'html.parser')


def remove_nbsp(lst):
    i = 1
    for x in lst[1:]:
        if x == '\xa0': # nbsp
            lst[i] = lst[i-1]
        i += 1
    return lst


# use 'List View'

bad_courses = ['COP']
days_of_week = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

# substring match id's with: MTG_COMP, MTG_SCHED, MTG_LOC, INSTR_LONG, MTG_DATES
comp = re.compile('MTG_COMP')
sched = re.compile('MTG_SCHED')
loc = re.compile('MTG_LOC')
instr = re.compile('INSTR_LONG')
dates = re.compile('MTG_DATES')

c = Calendar()

course_blocks = soup.find_all(class_='PSGROUPBOXWBO')[1:]
for block in course_blocks:
    course_title = block.find(class_='PAGROUPDIVIDER').text
    skip = False
    for course in bad_courses:
        if course in course_title:
            skip = True
            break
    if skip:
        continue

    components = remove_nbsp([x.text for x in block.find_all('span', id=comp)])
    schedule = remove_nbsp([x.text for x in block.find_all('span', id=sched)])
    locations = remove_nbsp([x.text for x in block.find_all('span', id=loc)])
    profs = remove_nbsp([x.text for x in block.find_all('span', id=instr)])
    start_end = remove_nbsp([x.text for x in block.find_all('span', id=dates)])

    for i in range(len(components)):
        splitted = start_end[i].split(' - ')
        start_date = splitted[0]
        end_date = splitted[1]

        time = schedule[i][3:].split(' - ')
        start_time = time[0]
        end_time = time[1].split(':')
        end_hour = int(end_time[0]) + (12 if end_time[1][2] == 'P' and int(end_time[0]) < 12 else 0)
        end_min = int(end_time[1][:2])
        dow = schedule[i][:2]

        dt = datetime.strptime(f'{start_time} {start_date}', '%I:%M%p %m/%d/%Y').replace(tzinfo=ZoneInfo('America/Toronto'))
        target = days_of_week.index(dow)
        offset = target - dt.weekday()
        dt = dt + timedelta(days=offset)

        e = Event()

        course_title_splitted = course_title.split(' - ')
        course_code = course_title_splitted[0]
        course_name = course_title_splitted[1]
        e.name = f'{components[i]} - {course_code}'
        e.description = f'{course_name}\nProf: {profs[i]}'

        e.location = locations[i]

        e.begin = dt
        e.end = dt.replace(hour=end_hour, minute=end_min)
        end_dt = datetime.strptime(end_date, '%m/%d/%Y') + timedelta(days=1)

        rule = f'FREQ=WEEKLY;UNTIL={end_dt.strftime("%Y%m%dT%H%M%SZ")}'
        e.extra.append(ContentLine(name="RRULE", value=rule))

        c.events.add(e)


five_weeks_later = dt + timedelta(weeks=5)

days_since_sunday = (five_weeks_later.weekday() + 1) % 7
rw_start = five_weeks_later - timedelta(days=days_since_sunday)
rw_end = rw_start + timedelta(days=6)

new_events = set()

for event in c.events:
    is_recurring = any(line.name == 'RRULE' for line in event.extra)

    if is_recurring:
        current_day = rw_start
        while current_day <= rw_end:
            if current_day.weekday() == event.begin.weekday():
                # IMPORTANT: EXDATE must match the start time of the event exactly
                # Format: YYYYMMDDTHHMMSS
                # we use the time from event.begin but the date from current_day
                exdate_dt = current_day.replace(
                    hour=event.begin.hour,
                    minute=event.begin.minute,
                    second=0,
                    tzinfo=event.begin.tzinfo
                )

                exdate_str = exdate_dt.strftime("%Y%m%dT%H%M%S")

                params = {}
                if event.begin.tzinfo:
                    params['TZID'] = [str(event.begin.tzinfo)]

                event.extra.append(ContentLine(
                    name='EXDATE',
                    params=params,
                    value=exdate_str
                ))

            current_day += timedelta(days=1)

        new_events.add(event)

    else:
        # one-off event filtering logic
        e_start = event.begin.datetime
        e_end = event.end.datetime

        # use aware comparison to avoid errors
        rw_start_aware = rw_start.replace(tzinfo=event.begin.tzinfo)
        rw_end_aware = rw_end.replace(hour=23, minute=59, tzinfo=event.begin.tzinfo)

        if not (e_start <= rw_end_aware and e_end >= rw_start_aware):
            new_events.add(event)


c.events = new_events

with open('schedule.ics', 'w') as f:
    f.writelines(c.serialize_iter())
