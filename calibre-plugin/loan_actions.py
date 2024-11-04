#
# Copyright (C) 2023 github.com/ping
#
# This file is part of the OverDrive Libby Plugin by ping
# OverDrive Libby Plugin for calibre / libby-calibre-plugin
#
# See https://github.com/ping/libby-calibre-plugin for more
# information
#
# Now being maintained at https://github.com/sgmoore/libby-calibre-plugin
#

from typing import Dict

from .libby import LibbyClient
from .models import get_media_title
from .utils import create_job_logger

# noinspection PyUnreachableCode
if False:
    load_translations = _ = lambda x=None: x  # noqa: E731

load_translations()


class LibbyLoanReturn:
    def __call__(
        self,
        gui,
        libby_client: LibbyClient,
        loan: Dict,
        log=None,
        abort=None,
        notifications=None,
    ):
        logger = create_job_logger(log)
        notifications.put((0.5, _("Returning")))
        libby_client.return_loan(loan)
        logger.info("Returned %s successfully.", get_media_title(loan))
        return loan


class LibbyLoanRenew:
    def __call__(
        self,
        gui,
        libby_client: LibbyClient,
        loan: Dict,
        log=None,
        abort=None,
        notifications=None,
    ):
        logger = create_job_logger(log)
        notifications.put((0.5, _("Renewing")))
        new_loan = libby_client.renew_loan(loan)
        logger.info("Renewed %s successfully.", get_media_title(loan))
        return new_loan
