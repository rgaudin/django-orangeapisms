#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

import pytest

from orangeapisms.utils import cleaned_msisdn


@pytest.fixture()
def correct_msisdn():
    return "+22376333005"


def test_msisdn_regular(correct_msisdn):
    assert correct_msisdn == cleaned_msisdn(correct_msisdn)


def test_msisdn_no_prefix(correct_msisdn):
    number = "76333005"
    assert correct_msisdn == cleaned_msisdn(number)


def test_msisdn_prefix_no_plus(correct_msisdn):
    number = "22376333005"
    assert correct_msisdn == cleaned_msisdn(number)


def test_msisdn_multiple_plus(correct_msisdn):
    number = "+223+76333005"
    assert correct_msisdn == cleaned_msisdn(number)


def test_msisdn_extra_spaces(correct_msisdn):
    number = "76 33 30 05"
    assert correct_msisdn == cleaned_msisdn(number)


def test_msisdn_extra_chars(correct_msisdn):
    number = "abc76333005def"
    assert correct_msisdn == cleaned_msisdn(number)
