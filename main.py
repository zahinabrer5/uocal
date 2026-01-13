import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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

def format_dt_local(dt):
    """Format datetime in local timezone for ICS (no Z suffix)"""
    return dt.strftime('%Y%m%dT%H%M%S')

# use 'List View'

bad_courses = ['COP']
days_of_week = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

# substring match id's with: MTG_COMP, MTG_SCHED, MTG_LOC, INSTR_LONG, MTG_DATES
comp = re.compile('MTG_COMP')
sched = re.compile('MTG_SCHED')
loc = re.compile('MTG_LOC')
instr = re.compile('INSTR_LONG')
dates = re.compile('MTG_DATES')

course_blocks = soup.find_all(class_='PSGROUPBOXWBO')[1:]

toronto_tz = ZoneInfo('America/Toronto')
events = []

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
        end_time_str = time[1]

        # Parse end time properly
        end_time_parts = end_time_str.split(':')
        end_hour_raw = int(end_time_parts[0])
        end_min = int(end_time_parts[1][:2])
        is_pm = 'PM' in end_time_str.upper()
        end_hour = end_hour_raw + (12 if is_pm and end_hour_raw < 12 else 0)
        if end_hour_raw == 12 and not is_pm:
            end_hour = 0

        dow = schedule[i][:2]

        try:
            dt_start = datetime.strptime(f'{start_time} {start_date}', '%I:%M%p %m/%d/%Y') \
                .replace(tzinfo=toronto_tz)
        except Exception as e:
            try:
                dt_start = datetime.strptime(f'{start_time} {start_date}', '%H:%M %m/%d/%Y') \
                    .replace(tzinfo=toronto_tz)
            except Exception as f:
                raise f

        target = days_of_week.index(dow)
        offset = target - dt_start.weekday()
        dt_start = dt_start + timedelta(days=offset)

        dt_end = dt_start.replace(hour=end_hour, minute=end_min)
        if dt_end <= dt_start:
            dt_end = dt_end + timedelta(days=1)

        course_title_splitted = course_title.split(' - ')
        course_code = course_title_splitted[0]
        course_name = course_title_splitted[1]

        event_name = f'{components[i][:3].upper()} {course_code}'
        event_desc = f'{course_name}\\nProf: {profs[i]}'
        event_loc = locations[i]

        end_dt = datetime.strptime(end_date, '%m/%d/%Y').replace(
            hour=23, minute=59, second=59, tzinfo=toronto_tz
        )

        events.append({
            'name': event_name,
            'description': event_desc,
            'location': event_loc,
            'start': dt_start,
            'end': dt_end,
            'until': end_dt
        })


# Write ICS file manually with proper timezone handling
with open('schedule.ics', 'w') as f:
    f.write('BEGIN:VCALENDAR\r\n')
    f.write('VERSION:2.0\r\n')
    f.write('PRODID:-//My Calendar//EN\r\n')
    f.write('CALSCALE:GREGORIAN\r\n')

    for event in events:
        f.write('BEGIN:VEVENT\r\n')
        f.write(f'DTSTART;TZID=America/Toronto:{format_dt_local(event["start"])}\r\n')
        f.write(f'DTEND;TZID=America/Toronto:{format_dt_local(event["end"])}\r\n')
        f.write(f'RRULE:FREQ=WEEKLY;UNTIL={format_dt_local(event["until"])}\r\n')
        f.write(f'SUMMARY:{event["name"]}\r\n')
        f.write(f'DESCRIPTION:{event["description"]}\r\n')
        f.write(f'LOCATION:{event["location"]}\r\n')
        f.write(f'UID:{hash(event["name"] + str(event["start"]))}@schedule\r\n')
        f.write('END:VEVENT\r\n')

    f.write('END:VCALENDAR\r\n')
