import sqlalchemy as sa
from sqlalchemy import types, literal, func, ARRAY
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import ColumnElement
from sqlalchemy.sql.elements import Grouping


class Any(ColumnElement):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs


class StringArray(ARRAY):
    def __init__(self, **kwargs):
        super().__init__(sa.String(), **kwargs)

    class comparator_factory(ARRAY.Comparator):
        def any(self, other):
            return Any(self.expr, other)


class StringArrayType(types.TypeDecorator):
    impl = sa.UnicodeText()

    class Comparator(sa.UnicodeText.Comparator):
        def any(self, other):
            return Any(self.expr, other)

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

    def dialect_impl(self, dialect):
        return super().dialect_impl(dialect)


@compiles(Any)
def compile_ancestor(element, compiler, **kw):
    other = '%' + str(element.rhs) + '%'
    expr = element.lhs.op('like')(other).self_group()
    return compiler.visit_grouping(expr)


@compiles(Any, 'postgresql')
def compile_ancestor(element, compiler, **kw):
    lhs = element.lhs
    rhs = element.rhs
    if isinstance(rhs, str):
        rhs = literal(rhs)
    expr = Grouping(rhs.op('=')(func.any(lhs)))
    return compiler.visit_grouping(expr)
