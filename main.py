import sys
from bs4 import BeautifulSoup
from pathlib import Path

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


def tag_index_ignore_class(tag, ignored_class):
    siblings = [
        child for child in tag.parent.find_all(recursive=False)
        if ignored_class not in (child.get('class') or [])
    ]
    return siblings.index(tag)


def weeknum_to_weekday(n):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']
    if not 0 <= n < 7:
        raise ValueError('Weekday must be in range 0–6')
    return days[n]


spans = soup.find_all('span', class_='SSSTEXTWEEKLY')
for span in spans:
    td = span.parent
    dow = weeknum_to_weekday(tag_index_ignore_class(td, 'PSLEVEL3GRIDODDROW'))
    block = [i for i in span.contents if isinstance(i, str)]
    print(dow, block)

# scrape from this page to get the start and end dates:
# https://www.uottawa.ca/study/important-academic-dates-deadlines
# or, it could be easier to calculate the start date manually and
# repeat 5 weeks before reading week and 7 weeks after
