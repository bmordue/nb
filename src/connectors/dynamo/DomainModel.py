from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute


class DomainModel(Model):
    """
    A DynamoDB Domain entry
    """

    class Meta:
        table_name = "domains"
        read_capacity_units = 1
        write_capacity_units = 1

    nb_hash = UnicodeAttribute(hash_key=True)
    domain = UnicodeAttribute()
    nb_url = UnicodeAttribute()
    toplevel = UnicodeAttribute()
    toplevel_new = UnicodeAttribute()
