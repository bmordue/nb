from pynamodb.models import Model
from pynamodb.attributes import NumberAttribute, UnicodeAttribute


class StoryModel(Model):
    """
    A DynamoDB Story entry
    """

    class Meta:
        table_name = "stories"
        read_capacity_units = 1
        write_capacity_units = 1

    nb_hash = UnicodeAttribute()
    hnurl = UnicodeAttribute(hash_key=True)
    url = UnicodeAttribute()
    added = UnicodeAttribute()
    comments = NumberAttribute(default=-1)
    starred = BooleanAttribute(default=True)
