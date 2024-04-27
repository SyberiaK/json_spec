import argparse
import json

from __init__ import generate_spec, spec_to_json, pprint_spec


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument('input', nargs='+',
                    help='.json files to convert to spec')
    ap.add_argument('-o', '--output',
                    help='specify the output file (otherwise just prints the resulted spec).')
    ap.add_argument('-d', '--depth', type=int, default=100,
                    help='the parsing depth limit (may throw `RecursionError` for deeply nested JSON with high values)')

    args = ap.parse_args()

    inputs = []
    for filepath in args.input:
        with open(filepath, encoding='utf-8') as f:
            inputs.append(json.load(f))

    spec = generate_spec(*inputs, max_depth=args.depth)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(spec_to_json(spec), f, indent=2)
    else:
        pprint_spec(spec)


if __name__ == '__main__':
    main()
