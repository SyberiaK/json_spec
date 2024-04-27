# json_spec

A handy script tool made to convert complex JSON data
into human-readable data specs.

## WARNING!
This script is mostly undocumented and untested. Use at your own risk. \
Also, the spec syntax is a self-made JSON-compatible format 
**meant to be just read by a human**. Although the inner spec format
can be parsed and manipulated with code, I doubt there would be 
any software to support it.

## Installation

### Prerequirements

- Python 3.8+ (3.11+ recommended) \
  https://www.python.org/downloads/

### Steps

1. Click on the green `Code` button -> `Download ZIP`
2. Unpack the contents in a directory of your choice.

## Usage

```pycon
python json_spec [-h] [-o OUTPUT] [-d DEPTH] [input ...]
```

**Example:**
```pycon
python json_spec sample1.json sample2.json sample3.json
```
This command will print out the resulted spec.

Notice that you can specify *multiple* input samples. 
This allows the script to construct union types from sample data.

### Additional arguments
- `-o` or `--output`: specify the output file
  (instead of printing the result)
- `-d` or `--depth`: set the parsing depth limit 
  (may throw `RecursionError` for deeply nested JSON with high values)

### Spec

The spec syntax supports all JSON types and handles union types with primitives.

**(!)**: Constructing union types **requires** multiple data samples. \
**(!)**: Union types with arrays/objects are **not** allowed (raise `ComplexUnionError`).

### API

I'm not sure whenever I'll make the API into its own package. \
For now, you can use it as-is by copying `__init__.py` content
into your project.

Most useful functions you need to know about:
- `generate_spec(*datas, max_depth: int = 10)` - generate a spec from data samples
- `spec_to_json(spec)` - convert a spec to JSON-compatible format
- `pprint_spec(spec)` - pretty-print a spec
