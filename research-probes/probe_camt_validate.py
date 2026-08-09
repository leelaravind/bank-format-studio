"""RESEARCH PROBE (disposable, not product code).

Verifies the collected camt.053 source pack:
1. every XSD in references/camt053 loads in xmlschema (primary) and lxml (fallback)
2. the declared targetNamespace matches the filename version
3. every sample in sample-data/public/camt053 is well-formed and validates
   against the matching bundled XSD (schemaLocation hints ignored; offline)

Run with the probe venv python.
"""
import pathlib
import re
import sys

import lxml.etree as etree
import xmlschema

ROOT = pathlib.Path(__file__).resolve().parent.parent
XSD_DIR = ROOT / "references" / "camt053"
SAMPLE_DIR = ROOT / "sample-data" / "public" / "camt053"

def main() -> int:
    schemas = {}
    print("== XSD load checks ==")
    for xsd in sorted(XSD_DIR.glob("*.xsd")):
        try:
            schema = xmlschema.XMLSchema(str(xsd))
            ns = schema.target_namespace
            m = re.search(r"camt\.053\.001\.(\d+)", ns or "")
            ok_ns = xsd.name.replace(".xsd", "") in (ns or "")
            print(f"  {xsd.name}: xmlschema OK, targetNamespace={ns}, filename-match={ok_ns}")
            # lxml cross-check
            etree.XMLSchema(etree.parse(str(xsd)))
            print(f"  {xsd.name}: lxml XMLSchema OK")
            schemas[ns] = schema
        except Exception as exc:  # noqa: BLE001
            print(f"  {xsd.name}: FAILED {type(exc).__name__}: {exc}")
    print("\n== Sample validation checks ==")
    failures = 0
    hardened = etree.XMLParser(resolve_entities=False, no_network=True, dtd_validation=False)
    for xml in sorted(SAMPLE_DIR.glob("*.xml")):
        try:
            tree = etree.parse(str(xml), hardened)
            ns = tree.getroot().tag.split("}")[0].strip("{")
            schema = schemas.get(ns)
            if schema is None:
                print(f"  {xml.name}: namespace {ns} has NO bundled XSD -> cannot validate")
                failures += 1
                continue
            errors = list(schema.iter_errors(str(xml)))
            if errors:
                print(f"  {xml.name}: INVALID ({len(errors)} errors); first: {errors[0].reason} at {errors[0].path}")
                failures += 1
            else:
                print(f"  {xml.name}: VALID against {ns.rsplit(':', 1)[-1]}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {xml.name}: FAILED {type(exc).__name__}: {exc}")
            failures += 1
    print(f"\nDone. Sample failures: {failures}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
