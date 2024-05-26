#!/usr/bin/env python

from functools import cached_property
from itertools import count
from unittest import TestCase, main
from unittest.mock import patch

from mm.properties import DataProperty, ClearableCachedPropertyMixin, get_cached_property_names


class ExampleClass(ClearableCachedPropertyMixin):
    foo = DataProperty('bar')

    def __init__(self):
        self.data = {'bar': 1}


class CachedPropertyTest(TestCase):
    def test_dict_attr_property_cached(self):
        obj = ExampleClass()
        self.assertEqual(obj.foo, 1)
        obj.data['bar'] = 2
        self.assertEqual(obj.foo, 1)

    def test_dict_attr_property_reset(self):
        obj = ExampleClass()
        self.assertEqual(obj.foo, 1)
        obj.data['bar'] = 2
        obj.clear_cached_properties()
        self.assertEqual(obj.foo, 2)

    def test_get_cached_property_names(self):
        class D1:
            pass

        class Foo:  # noqa
            a = D1()
            b = DataProperty('b')

            @cached_property
            def c(self):
                return 1

            @property
            def d(self):
                return 2

        self.assertSetEqual({'b', 'c'}, get_cached_property_names(Foo))
        with patch('mm.properties.is_cached_property') as is_cached_property_mock:
            self.assertSetEqual({'b', 'c'}, get_cached_property_names(Foo()))
            is_cached_property_mock.assert_not_called()  # The result should be cached from the previous call above

    def test_clear_properties(self):
        class Foo(ClearableCachedPropertyMixin):
            def __init__(self):
                self.counter = count()

            @cached_property
            def bar(self):
                return next(self.counter)

            def baz(self):
                return 1

        foo = Foo()
        self.assertEqual(0, foo.bar)
        self.assertEqual(0, foo.bar)
        foo.clear_cached_properties()
        foo.clear_cached_properties()  # again for unittest to see key error. . .
        self.assertEqual(1, foo.bar)

    def test_clear_specific_properties(self):
        class Foo(ClearableCachedPropertyMixin):
            def __init__(self):
                self.counter = count()
                self.counter_2 = count()

            @cached_property
            def bar(self):
                return next(self.counter)

            @cached_property
            def baz(self):
                return next(self.counter_2)

        foo = Foo()
        self.assertEqual(0, foo.bar)
        self.assertEqual(0, foo.baz)
        foo.clear_cached_properties('baz')
        self.assertEqual(0, foo.bar)
        self.assertEqual(1, foo.baz)
        foo.clear_cached_properties(skip='baz')
        self.assertEqual(1, foo.bar)
        self.assertEqual(1, foo.baz)
        foo.clear_cached_properties(skip=['baz'])
        self.assertEqual(2, foo.bar)
        self.assertEqual(1, foo.baz)


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
