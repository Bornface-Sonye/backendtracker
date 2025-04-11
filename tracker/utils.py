import random
import string

from .models import Complaint

def generate_unique_complaint_code(max_attempts=10):
    for _ in range(max_attempts):
        code = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(random.choices(string.digits, k=3))
        if not Complaint.objects.filter(complaint_code=code).exists():
            return code
    raise Exception("Unable to generate unique complaint code after multiple attempts.")
