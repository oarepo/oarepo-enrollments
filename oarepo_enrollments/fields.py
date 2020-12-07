import sqlalchemy as sa
from sqlalchemy import types


class StringArrayType(types.TypeDecorator):
    impl = sa.UnicodeText()

    class Comparator(sa.UnicodeText.Comparator):
        def any(self, other):
            other = '%' + str(other) + '%'
            return self.op('like')(other).self_group()

    comparator_factory = Comparator

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, str):
                value = self.process_result_value(value, None)
            return ',' + ','.join([str(x).strip() for x in value]) + ','

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.strip(',')
            return value.split(',')
