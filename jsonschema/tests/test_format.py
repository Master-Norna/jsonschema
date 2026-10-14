"""
Tests for the parts of jsonschema related to the :kw:`format` keyword.
"""

from unittest import TestCase

from jsonschema import FormatChecker, ValidationError
from jsonschema.exceptions import FormatError
from jsonschema.validators import (
    Draft3Validator,
    Draft4Validator,
    Draft6Validator,
    Draft7Validator,
    Draft201909Validator,
    Draft202012Validator,
)

BOOM = ValueError("Boom!")
BANG = ZeroDivisionError("Bang!")


def boom(thing):
    if thing == "bang":
        raise BANG
    raise BOOM


class TestFormatChecker(TestCase):
    def test_it_can_validate_no_formats(self):
        checker = FormatChecker(formats=())
        self.assertFalse(checker.checkers)

    def test_it_raises_a_key_error_for_unknown_formats(self):
        with self.assertRaises(KeyError):
            FormatChecker(formats=["o noes"])

    def test_it_can_register_cls_checkers(self):
        original = dict(FormatChecker.checkers)
        self.addCleanup(FormatChecker.checkers.pop, "boom")
        with self.assertWarns(DeprecationWarning):
            FormatChecker.cls_checks("boom")(boom)
        self.assertEqual(
            FormatChecker.checkers,
            dict(original, boom=(boom, ())),
        )

    def test_it_can_register_checkers(self):
        checker = FormatChecker()
        checker.checks("boom")(boom)
        self.assertEqual(
            checker.checkers,
            dict(FormatChecker.checkers, boom=(boom, ())),
        )

    def test_it_catches_registered_errors(self):
        checker = FormatChecker()
        checker.checks("boom", raises=type(BOOM))(boom)

        with self.assertRaises(FormatError) as cm:
            checker.check(instance=12, format="boom")

        self.assertIs(cm.exception.cause, BOOM)
        self.assertIs(cm.exception.__cause__, BOOM)
        self.assertEqual(str(cm.exception), "12 is not a 'boom'")

        # Unregistered errors should not be caught
        with self.assertRaises(type(BANG)):
            checker.check(instance="bang", format="boom")

    def test_format_error_causes_become_validation_error_causes(self):
        checker = FormatChecker()
        checker.checks("boom", raises=ValueError)(boom)
        validator = Draft4Validator({"format": "boom"}, format_checker=checker)

        with self.assertRaises(ValidationError) as cm:
            validator.validate("BOOM")

        self.assertIs(cm.exception.cause, BOOM)
        self.assertIs(cm.exception.__cause__, BOOM)

    def test_format_checkers_come_with_defaults(self):
        # This is bad :/ but relied upon.
        # The docs for quite awhile recommended people do things like
        # validate(..., format_checker=FormatChecker())
        # We should change that, but we can't without deprecation...
        checker = FormatChecker()
        with self.assertRaises(FormatError):
            checker.check(instance="not-an-ipv4", format="ipv4")

    def test_repr(self):
        checker = FormatChecker(formats=())
        checker.checks("foo")(lambda thing: True)  # pragma: no cover
        checker.checks("bar")(lambda thing: True)  # pragma: no cover
        checker.checks("baz")(lambda thing: True)  # pragma: no cover
        self.assertEqual(
            repr(checker),
            "<FormatChecker checkers=['bar', 'baz', 'foo']>",
        )


class TestNoTrailingNewline(TestCase):
    """
    A newline (U+000A) is not part of the date-time, time, URI, IRI, or
    host-name grammars, but several of the packages these checkers
    delegate to (e.g. rfc3339-validator, rfc3987, fqdn) accept a single
    *trailing* newline.

    The instances below are the corresponding "trailing newline is
    invalid" cases from the official test suite, together with the same
    instances minus the newline, which must remain valid.
    """

    CASES = [
        # (validator, format, valid instance)
        (Draft3Validator, "date-time", "1985-04-12T23:20:50Z"),
        (Draft3Validator, "uri", "http://foo.bar/"),
        (Draft3Validator, "host-name", "example.com"),
        (Draft4Validator, "date-time", "1985-04-12T23:20:50Z"),
        (Draft4Validator, "uri", "http://foo.bar/"),
        (Draft4Validator, "hostname", "example.com"),
        (Draft6Validator, "date-time", "1985-04-12T23:20:50Z"),
        (Draft6Validator, "uri", "http://foo.bar/"),
        (Draft6Validator, "uri-reference", "example.com"),
        (Draft6Validator, "hostname", "example.com"),
    ]

    for _validator in (
        Draft7Validator,
        Draft201909Validator,
        Draft202012Validator,
    ):
        CASES.append((_validator, "date-time", "1985-04-12T23:20:50Z"))
        CASES.append((_validator, "time", "08:30:06Z"))
        CASES.append((_validator, "uri", "http://foo.bar/"))
        CASES.append((_validator, "uri-reference", "example.com"))
        CASES.append((_validator, "iri", "http://ƒøø.ßår/"))
        CASES.append((_validator, "iri-reference", "/âππ"))
        CASES.append((_validator, "hostname", "example.com"))

    def _assert_format(self, validator, fmt, instance, valid):
        if fmt not in validator.FORMAT_CHECKER.checkers:
            self.skipTest(f"{fmt!r} checker not registered")
        validator_instance = validator(
            {"format": fmt},
            format_checker=validator.FORMAT_CHECKER,
        )
        self.assertEqual(validator_instance.is_valid(instance), valid)

    def test_trailing_newline_is_invalid(self):
        for validator, fmt, instance in self.CASES:
            with self.subTest(validator=validator.__name__, format=fmt):
                self._assert_format(
                    validator,
                    fmt,
                    instance + "\n",
                    valid=False,
                )
                self._assert_format(
                    validator,
                    fmt,
                    instance + "\r\n",
                    valid=False,
                )

    def test_instances_without_newline_still_valid(self):
        for validator, fmt, instance in self.CASES:
            with self.subTest(validator=validator.__name__, format=fmt):
                self._assert_format(validator, fmt, instance, valid=True)
