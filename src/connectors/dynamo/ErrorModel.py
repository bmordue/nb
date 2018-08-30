from pynamodb.models import Model
from pynamodb.attributes import NumberAttribute, UnicodeAttribute

class ErrorModel(Model):
    """
    DynamoDB Error record
    """
    class Meta:
        table_name = "error"
        read_capacity_units = 1
        write_capacity_units = 1
    url = UnicodeAttribute(hash_key=True)
    status_code = NumberAttribute()
    headers = UnicodeAttribute(null=True)
    body = UnicodeAttribute(null=True)
    ttl = NumberAttribute()
