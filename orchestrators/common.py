import dateparser

def parse_datetime(datetime_str: str):
    dt = dateparser.parse(datetime_str, languages=['ru'])
    return dt
