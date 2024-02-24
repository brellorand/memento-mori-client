"""
Helpers for serializing Python data structures to JSON or YAML
"""

import json
from collections import UserDict
from collections.abc import Mapping, KeysView, ValuesView
from datetime import datetime, date, timedelta
from json.encoder import JSONEncoder, encode_basestring_ascii, encode_basestring  # noqa

try:
    import yaml
except ImportError:
    yaml = None

__all__ = ['OUTPUT_FORMATS', 'YAML', 'pprint', 'yaml_dump', 'PermissiveJSONEncoder', 'CompactJSONEncoder']

OUTPUT_FORMATS = ['json', 'json-pretty']
YAML = yaml is not None


if yaml is None:

    class IndentedYamlDumper:
        pass

else:
    OUTPUT_FORMATS.append('yaml')

    class IndentedYamlDumper(yaml.SafeDumper):
        """This indents lists that are nested in dicts in the same way as the Perl yaml library"""
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)


def pprint(out_fmt: str, data):
    if out_fmt == 'json':
        print(json.dumps(data, ensure_ascii=False))
    elif out_fmt == 'json-pretty':
        print(json.dumps(data, indent=4, ensure_ascii=False, cls=CompactJSONEncoder))
    elif out_fmt == 'yaml':
        print(yaml_dump(data, indent_nested_lists=True))
    else:
        raise ValueError(f'Invalid {out_fmt=} - choose from {OUTPUT_FORMATS}')


def prep_for_yaml(obj):
    if isinstance(obj, UserDict):
        obj = obj.data
    # noinspection PyTypeChecker
    if isinstance(obj, Mapping):
        return {prep_for_yaml(k): prep_for_yaml(v) for k, v in obj.items()}
    elif isinstance(obj, (set, KeysView)):
        return [prep_for_yaml(v) for v in sorted(obj)]
    elif isinstance(obj, (list, tuple, map, ValuesView)):
        return [prep_for_yaml(v) for v in obj]
    elif isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return obj.hex(' ', -4)
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S %Z')
    elif isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, (type, timedelta)):
        return str(obj)
    elif hasattr(obj, '__serializable__'):
        return obj.__serializable__()
    elif obj is ...:
        return '...'
    else:
        return obj


def yaml_dump(
    data,
    force_single_yaml: bool = False,
    indent_nested_lists: bool = True,
    default_flow_style: bool = None,
    split_list_eles: bool = True,
    sanitize: bool = True,
    **kwargs,
) -> str:
    if yaml is None:
        raise RuntimeError('Missing optional dependency: PyYAML')
    if sanitize:
        data = prep_for_yaml(data)

    kwargs.setdefault('explicit_start', True)
    kwargs.setdefault('width', float('inf'))
    kwargs.setdefault('allow_unicode', True)
    kwargs.setdefault('sort_keys', False)
    if indent_nested_lists:
        kwargs['Dumper'] = IndentedYamlDumper

    if isinstance(data, (dict, str)) or force_single_yaml:
        kwargs.setdefault('default_flow_style', False if default_flow_style is None else default_flow_style)
        formatted = yaml.dump(data, **kwargs)
    elif split_list_eles:
        kwargs.setdefault('default_flow_style', False if default_flow_style is None else default_flow_style)
        formatted = '\n'.join(_clean_end(yaml.dump(c, **kwargs)) for c in data)
    else:
        kwargs.setdefault('default_flow_style', True if default_flow_style is None else default_flow_style)
        formatted = yaml.dump_all(data, **kwargs)

    return _clean_end(formatted)


def _clean_end(formatted: str) -> str:
    if formatted.endswith('...\n'):
        formatted = formatted[:-4]
    if formatted.endswith('\n'):
        formatted = formatted[:-1]
    return formatted


class PermissiveJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, (set, KeysView)):
            return sorted(o)
        elif isinstance(o, ValuesView):
            return list(o)
        elif isinstance(o, Mapping):
            return dict(o)
        elif isinstance(o, bytes):
            try:
                return o.decode('utf-8')
            except UnicodeDecodeError:
                return o.hex(' ', -4)
        elif isinstance(o, datetime):
            return o.isoformat(' ')
        elif isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        elif isinstance(o, (type, timedelta)):
            return str(o)
        return super().default(o)


class CompactJSONEncoder(PermissiveJSONEncoder):
    """A JSON Encoder that puts small containers on single lines."""

    CONTAINER_TYPES = (list, tuple, dict)

    def __init__(self, *args, indent: int = None, max_line_len: int = 100, max_line_items: int = 10, **kwargs):
        # Using this class without indentation is pointless - force indent=4 if not specified
        kwargs.setdefault('ensure_ascii', False)
        super().__init__(*args, indent=indent or 4, **kwargs)
        self._indentation_level = 0
        self._max_line_len = max_line_len
        self._max_line_items = max_line_items

    def encode(self, o):
        match o:
            case list() | tuple():
                return self._encode_list(o)
            case dict():
                return self._encode_object(o)
            case float():
                return self._encode_float(o)
            case str():
                return encode_basestring_ascii(o) if self.ensure_ascii else encode_basestring(o)
            case _:
                return json.dumps(
                    o,
                    skipkeys=self.skipkeys,
                    ensure_ascii=self.ensure_ascii,
                    check_circular=self.check_circular,
                    allow_nan=self.allow_nan,
                    sort_keys=self.sort_keys,
                    indent=self.indent,
                    separators=(self.item_separator, self.key_separator),
                    default=self.__dict__.get('default'),  # Only set if a default func was provided
                    cls=PermissiveJSONEncoder,
                )

    def _encode_float(self, o: float, _repr=float.__repr__, _inf=float('inf'), _neginf=-float('inf')):
        # Mostly copied from the implementation in json.encoder.JSONEncoder.iterencode
        if o != o:
            text = 'NaN'
        elif o == _inf:
            text = 'Infinity'
        elif o == _neginf:
            text = '-Infinity'
        else:
            return _repr(o)  # noqa

        if not self.allow_nan:
            raise ValueError(f'Out of range float values are not JSON compliant: {o!r}')
        return text

    def _encode_list(self, obj: list) -> str:
        if self._len_okay_and_not_nested(obj):
            parts = [self.encode(v) for v in obj]
            if self._str_len_is_below_max(parts):
                return f'[{", ".join(parts)}]'

        self._indentation_level += 1
        content = ',\n'.join(self.indent_str + self.encode(v) for v in obj)
        self._indentation_level -= 1
        return f'[\n{content}\n{self.indent_str}]'

    def _encode_object(self, obj: dict):
        if not obj:
            return '{}'

        # ensure keys are converted to strings
        obj = {str(k) if k is not None else 'null': v for k, v in obj.items()}
        if self.sort_keys:
            obj = dict(sorted(obj.items()))

        dump_str = encode_basestring_ascii if self.ensure_ascii else encode_basestring
        if self._len_okay_and_not_nested(obj):
            parts = [f'{dump_str(k)}: {self.encode(v)}' for k, v in obj.items()]
            if self._str_len_is_below_max(parts):
                return f'{{{", ".join(parts)}}}'

        self._indentation_level += 1
        output = ',\n'.join(f'{self.indent_str}{dump_str(k)}: {self.encode(v)}' for k, v in obj.items())
        self._indentation_level -= 1
        return f'{{\n{output}\n{self.indent_str}}}'

    def iterencode(self, o, **kwargs):
        """Required to also work with `json.dump`."""
        return self.encode(o)

    def _len_okay_and_not_nested(self, obj: list | tuple | dict) -> bool:
        return (
            len(obj) <= self._max_line_items
            and not any(isinstance(v, self.CONTAINER_TYPES) for v in (obj.values() if isinstance(obj, dict) else obj))
        )

    def _str_len_is_below_max(self, parts: list[str]) -> bool:
        return (2 + sum(map(len, parts)) + (2 * len(parts))) <= self._max_line_len

    @property
    def indent_str(self) -> str:
        if isinstance(self.indent, int):
            return ' ' * (self._indentation_level * self.indent)
        elif isinstance(self.indent, str):
            return self._indentation_level * self.indent
        else:
            raise TypeError(f'indent must either be of type int or str (found: {self.indent.__class__.__name__})')
