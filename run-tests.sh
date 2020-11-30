#!/usr/bin/env sh
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 UCT Prague.
#
# oarepo-validate is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

# pydocstyle oarepo_validate tests docs && \
# isort -rc -c -df && \
# check-manifest --ignore ".travis-*" && \
python setup.py test
