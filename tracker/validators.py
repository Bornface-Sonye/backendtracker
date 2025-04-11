import re
from django.core.exceptions import ValidationError

def validate_reg_no(value):
    # Pattern explanation:
    # - Three letters (uppercase or lowercase) at the start
    # - A forward slash ('/')
    # - One letter (uppercase or lowercase)
    # - Another forward slash ('/')
    # - Two digits, followed by a hyphen ('-')
    # - Five digits, followed by a forward slash ('/')
    # - Four digits at the end (for the year)
    if not re.match(r'^[A-Za-z]{3}/[A-Za-z]/\d{2}-\d{5}/\d{4}$', str(value)):
        raise ValidationError(f'{value} is not a valid registration number. Expected format: ABC/D/01-00123/2023')




def validate_kenyan_phone_number(value):
    value_str = str(value)
    if not re.match(r'^(?:\+254|0)?7\d{8}$', value_str):
        raise ValidationError(
            f'{value} is not a valid Kenyan phone number. It must be in the format 0798073204 or +254798073404.'
        )
