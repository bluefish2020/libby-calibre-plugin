#
# Copyright (C) 2023 github.com/ping
#
# This file is part of the OverDrive Libby Plugin by ping
# OverDrive Libby Plugin for calibre / libby-calibre-plugin
#
# See https://github.com/ping/libby-calibre-plugin for more
# information
#
from threading import Lock
from typing import Dict, List

from calibre.constants import DEBUG
from qt.core import (
    QAbstractItemView,
    QButtonGroup,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QRadioButton,
    QThread,
    QWidget,
    Qt,
)

from .base_search import SearchBaseDialog
from .widgets import DefaultQPushButton, DefaultQTableView
from ..compat import (
    QHeaderView_ResizeMode_ResizeToContents,
    QHeaderView_ResizeMode_Stretch,
    _c,
)
from ..config import (
    BorrowActions,
    PREFS,
    PreferenceKeys,
    SearchMode,
)
from ..libby import LibbyFormats
from ..models import (
    LibbySearchModel,
    LibbySearchSortFilterModel,
)
from ..overdrive import LibraryMediaSearchParams
from ..utils import PluginImages
from ..workers import OverDriveLibraryMediaSearchWorker

# noinspection PyUnreachableCode
if False:
    load_translations = _ = ngettext = lambda x=None, y=None, z=None: x

load_translations()


class AdvancedSearchDialogMixin(SearchBaseDialog):
    def __init__(self, *args):
        super().__init__(*args)

        self._lib_search_threads: List[QThread] = []
        self._lib_search_result_sets: Dict[str, List[Dict]] = {}
        self.lock = Lock()

        adv_search_widget = QWidget()
        adv_search_widget.layout = QGridLayout()
        adv_search_widget.setLayout(adv_search_widget.layout)
        widget_row_pos = 0

        form_fields_layout = QFormLayout()
        form_fields_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_fields_layout.setHorizontalSpacing(20)
        adv_search_widget.layout.addLayout(
            form_fields_layout, widget_row_pos, 0, 1, self.view_hspan - 1
        )

        # Title Query textbox
        self.adv_query_txt = QLineEdit(self)
        self.adv_query_txt.setClearButtonEnabled(True)
        form_fields_layout.addRow(_("Query"), self.adv_query_txt)

        # Title Query textbox
        self.title_txt = QLineEdit(self)
        self.title_txt.setClearButtonEnabled(True)
        form_fields_layout.addRow(_c("Title"), self.title_txt)

        # Creator Query textbox
        self.creator_txt = QLineEdit(self)
        self.creator_txt.setClearButtonEnabled(True)
        form_fields_layout.addRow(_c("Author"), self.creator_txt)

        # Identifier Query textbox
        self.identifier_txt = QLineEdit(self)
        self.identifier_txt.setClearButtonEnabled(True)
        form_fields_layout.addRow(_("ISBN"), self.identifier_txt)

        self.availability_btn_group = QButtonGroup(self)
        self.availability_all_rb = QRadioButton(_("All"), self)
        self.availability_only_available_rb = QRadioButton(_("Available now"), self)
        self.availability_only_prelease_rb = QRadioButton(_("Coming soon"), self)
        availability_rb = (
            self.availability_all_rb,
            self.availability_only_available_rb,
            self.availability_only_prelease_rb,
        )
        self.availability_rb_layout = QHBoxLayout()
        for rb in availability_rb:
            self.availability_btn_group.addButton(rb)
            self.availability_rb_layout.addWidget(rb)
        form_fields_layout.addRow(_("Availability"), self.availability_rb_layout)

        # Search button
        self.adv_search_btn = DefaultQPushButton(
            _c("Search"), self.resources[PluginImages.Search], self
        )
        self.adv_search_btn.clicked.connect(self.adv_search_btn_clicked)
        adv_search_widget.layout.addWidget(
            self.adv_search_btn,
            widget_row_pos,
            self.view_hspan - 1,
            alignment=Qt.AlignTop,
        )
        widget_row_pos += 1

        self.adv_search_model = LibbySearchModel(None, [], self.db)
        self.adv_search_proxy_model = LibbySearchSortFilterModel(
            self, model=self.adv_search_model
        )
        self.adv_search_proxy_model.setSourceModel(self.adv_search_model)

        # The main search results list
        self.adv_search_results_view = DefaultQTableView(
            self, model=self.adv_search_proxy_model, min_width=self.min_view_width
        )
        self.adv_search_results_view.setSelectionMode(QAbstractItemView.SingleSelection)
        # context menu
        self.adv_search_results_view.customContextMenuRequested.connect(
            self.adv_search_results_view_context_menu_requested
        )
        # selection change
        self.adv_search_results_view.selectionModel().selectionChanged.connect(
            self.adv_search_results_view_selection_model_selectionchanged
        )
        # debug display
        self.adv_search_results_view.doubleClicked.connect(
            lambda mi: self.display_debug("Search Result", mi.data(Qt.UserRole))
            if DEBUG and mi.column() == self.adv_search_model.columnCount() - 1
            else self.show_book_details(mi.data(Qt.UserRole))
        )
        horizontal_header = self.adv_search_results_view.horizontalHeader()
        for col_index in range(self.adv_search_model.columnCount()):
            horizontal_header.setSectionResizeMode(
                col_index,
                QHeaderView_ResizeMode_Stretch
                if col_index == 0
                else QHeaderView_ResizeMode_ResizeToContents,
            )
        adv_search_widget.layout.addWidget(
            self.adv_search_results_view,
            widget_row_pos,
            0,
            self.view_vspan,
            self.view_hspan,
        )
        widget_row_pos += 1

        if hasattr(self, "search_tab_index"):
            self.toggle_advsearch_mode_btn = DefaultQPushButton(
                "", self.resources[PluginImages.Switch], self
            )
            self.toggle_advsearch_mode_btn.setToolTip(_("Basic Search"))
            self.toggle_advsearch_mode_btn.setMaximumWidth(
                self.toggle_advsearch_mode_btn.height()
            )
            self.toggle_advsearch_mode_btn.clicked.connect(
                self.toggle_advsearch_mode_btn_clicked
            )
            adv_search_widget.layout.addWidget(
                self.toggle_advsearch_mode_btn, widget_row_pos, 0
            )

        borrow_action_default_is_borrow = PREFS[
            PreferenceKeys.LAST_BORROW_ACTION
        ] == BorrowActions.BORROW or not hasattr(self, "download_loan")

        self.adv_search_borrow_btn = DefaultQPushButton(
            _("Borrow")
            if borrow_action_default_is_borrow
            else _("Borrow and Download"),
            self.resources[PluginImages.Add],
            self,
        )
        adv_search_widget.layout.addWidget(
            self.adv_search_borrow_btn, widget_row_pos, self.view_hspan - 1
        )
        self.adv_hold_btn = DefaultQPushButton(_("Place Hold"), None, self)
        adv_search_widget.layout.addWidget(
            self.adv_hold_btn, widget_row_pos, self.view_hspan - 2
        )
        # set last 2 col's min width (buttons)
        for i in (1, 2):
            adv_search_widget.layout.setColumnMinimumWidth(
                adv_search_widget.layout.columnCount() - i, self.min_button_width
            )
        for col_num in range(0, adv_search_widget.layout.columnCount() - 2):
            adv_search_widget.layout.setColumnStretch(col_num, 1)

        self.adv_search_tab_index = self.add_tab(
            adv_search_widget, _("Advanced Search")
        )
        self.last_borrow_action_changed.connect(self.rebind_advsearch_borrow_btn)
        self.sync_starting.connect(self.base_sync_starting_advsearch)
        self.sync_ended.connect(self.base_sync_ended_advsearch)
        self.loan_added.connect(self.loan_added_advsearch)
        self.loan_removed.connect(self.loan_removed_advsearch)
        self.hold_added.connect(self.hold_added_advsearch)
        self.hold_removed.connect(self.hold_removed_advsearch)

    def toggle_advsearch_mode_btn_clicked(self):
        if hasattr(self, "search_tab_index"):
            PREFS[PreferenceKeys.SEARCH_MODE] = SearchMode.BASIC
            self.search_mode_changed.emit(SearchMode.BASIC)
            self.tabs.setCurrentIndex(self.search_tab_index)

    def base_sync_starting_advsearch(self):
        self.adv_search_borrow_btn.setEnabled(False)
        self.adv_search_model.sync({})

    def base_sync_ended_advsearch(self, value):
        self.adv_search_borrow_btn.setEnabled(True)
        self.adv_search_model.sync(value)

    def rebind_advsearch_borrow_btn(self, last_borrow_action: str):
        borrow_action_default_is_borrow = (
            last_borrow_action == BorrowActions.BORROW
            or not hasattr(self, "download_loan")
        )
        self.adv_search_borrow_btn.setText(
            _("Borrow") if borrow_action_default_is_borrow else _("Borrow and Download")
        )
        self.adv_search_borrow_btn.borrow_menu = None
        self.adv_search_borrow_btn.setMenu(None)
        self.adv_search_results_view.selectionModel().clearSelection()

    def loan_added_advsearch(self, loan: Dict):
        self.adv_search_model.add_loan(loan)
        self.adv_search_results_view.selectionModel().clearSelection()

    def loan_removed_advsearch(self, loan: Dict):
        self.adv_search_model.remove_loan(loan)
        self.adv_search_results_view.selectionModel().clearSelection()

    def hold_added_advsearch(self, hold: Dict):
        self.adv_search_model.add_hold(hold)
        self.adv_search_results_view.selectionModel().clearSelection()

    def hold_removed_advsearch(self, hold: Dict):
        self.adv_search_model.remove_hold(hold)
        self.adv_search_results_view.selectionModel().clearSelection()

    def adv_search_results_view_selection_model_selectionchanged(self):
        self.view_selection_model_selectionchanged(
            self.adv_search_borrow_btn,
            self.adv_hold_btn,
            self.adv_search_results_view,
            self.adv_search_model,
        )

    def adv_search_results_view_context_menu_requested(self, pos):
        self.view_context_menu_requested(
            pos, self.adv_search_results_view, self.adv_search_model
        )

    def _adv_reset_borrow_hold_buttons(self):
        self.adv_search_borrow_btn.borrow_menu = None
        self.adv_search_borrow_btn.setMenu(None)
        self.adv_search_borrow_btn.setEnabled(True)
        self.adv_hold_btn.hold_menu = None
        self.adv_hold_btn.setMenu(None)
        self.adv_hold_btn.setEnabled(True)

    def _has_running_search(self, asked_by=None) -> bool:
        for t in self._lib_search_threads:
            if asked_by and asked_by == t.library_key:
                continue
            if t.isRunning():
                return True
        return False

    def adv_search_btn_clicked(self):
        self.adv_search_model.sync({"search_results": []})
        self.adv_search_results_view.sortByColumn(-1, Qt.AscendingOrder)
        self._reset_borrow_hold_buttons()
        if self._has_running_search():
            return

        if not PREFS[PreferenceKeys.INCL_NONDOWNLOADABLE_TITLES]:
            formats = [
                LibbyFormats.EBookEPubAdobe,
                LibbyFormats.EBookPDFAdobe,
                LibbyFormats.EBookEPubOpen,
                LibbyFormats.EBookPDFOpen,
                LibbyFormats.MagazineOverDrive,
            ]
        else:
            formats = [
                LibbyFormats.EBookEPubAdobe,
                LibbyFormats.EBookPDFAdobe,
                LibbyFormats.EBookEPubOpen,
                LibbyFormats.EBookPDFOpen,
                LibbyFormats.MagazineOverDrive,
                LibbyFormats.EBookKindle,
                LibbyFormats.AudioBookMP3,
                LibbyFormats.AudioBookOverDrive,
            ]
        query = LibraryMediaSearchParams(
            query=self.adv_query_txt.text(),
            title=self.title_txt.text(),
            creator=self.creator_txt.text(),
            identifier=self.identifier_txt.text(),
            show_only_available=self.availability_only_available_rb.isChecked(),
            show_only_prelease=self.availability_only_prelease_rb.isChecked(),
            formats=formats,
            per_page=PREFS[PreferenceKeys.SEARCH_RESULTS_MAX],
        )
        if query.is_empty():
            return

        self.adv_search_btn.setText(_c("Searching..."))
        self.adv_search_btn.setEnabled(False)
        self.setCursor(Qt.WaitCursor)
        library_keys = self.adv_search_model.limited_library_keys()
        self.status_bar.showMessage(
            ngettext(
                "Searching across {n} library...",
                "Searching across {n} libraries...",
                len(library_keys),
            ).format(n=len(library_keys))
        )
        self._lib_search_threads = []
        self._lib_search_result_sets = {}

        for library_key in library_keys:
            search_thread = self._get_adv_search_thread(
                self.overdrive_client, library_key, query
            )
            self._lib_search_threads.append(search_thread)
            search_thread.start()

    def adv_search_for(self, title: str, author: str):
        self.tabs.setCurrentIndex(self.adv_search_tab_index)
        self.title_txt.setText(title)
        self.creator_txt.setText(author)
        self.availability_all_rb.setChecked(True)
        self.identifier_txt.setText("")
        self.adv_search_btn.setFocus(Qt.OtherFocusReason)
        self.adv_search_btn.animateClick()

    def _process_search_results(self, library_key, search_items: List[Dict]):
        with self.lock:
            self._lib_search_result_sets[library_key] = search_items
            found_library_keys = self._lib_search_result_sets.keys()
            if len(found_library_keys) != len(self._lib_search_threads):
                pending_libraries = [
                    t.library_key
                    for t in self._lib_search_threads
                    if t.library_key not in found_library_keys
                ]
                self.status_bar.showMessage(
                    _("Waiting for {libraries}...").format(
                        libraries=", ".join(pending_libraries)
                    )
                )
                return

            self.adv_search_btn.setText(_c("Search"))
            self.adv_search_btn.setEnabled(True)
            self.unsetCursor()
            self.status_bar.clearMessage()
            combined_search_results: Dict[str, Dict] = {}
            for lib_key, result_items in self._lib_search_result_sets.items():
                for item_rank, item in enumerate(result_items, start=1):
                    site_availability = {}
                    for k in (
                        "advantageKey",
                        "availabilityType",
                        "availableCopies",
                        "estimatedWaitDays",
                        "formats",
                        "holdsCount",
                        "holdsRatio",
                        "isAdvantageFiltered",
                        "isAvailable",
                        "isOwned",
                        "isRecommendableToLibrary",
                        "isFastlane",
                        "isHoldable",
                        "juvenileEligible",
                        "luckyDayAvailableCopies",
                        "luckyDayOwnedCopies",
                        "ownedCopies",
                        "visitorEligible",
                        "youngAdultEligible",
                    ):
                        if k in item:
                            site_availability[k] = item.pop(k)
                    site_availability["advantageKey"] = library_key
                    item.setdefault("siteAvailabilities", {})
                    item.setdefault("__item_ranks", [])
                    item.setdefault("formats", [])
                    title_id = item["id"]
                    combined_search_results.setdefault(title_id, item)
                    # merge site availabilities
                    combined_search_results[title_id]["siteAvailabilities"][
                        lib_key
                    ] = site_availability
                    # merge item ranks
                    combined_search_results[title_id]["__item_ranks"].append(item_rank)
                    # merge formats
                    existing_format_ids = [
                        f["id"]
                        for f in combined_search_results[title_id].get("formats", [])
                    ]
                    for f in site_availability.get("formats", []):
                        if f["id"] not in existing_format_ids:
                            combined_search_results[title_id]["formats"].append(f)

            ordered_search_result_items = sorted(
                combined_search_results.values(),
                key=lambda r: (
                    sum(r["__item_ranks"]) / len(r["__item_ranks"]),  # average rank
                    1 / len(r["__item_ranks"]),
                ),
            )
            self.status_bar.showMessage(
                ngettext(
                    "{n} result found",
                    "{n} results found",
                    len(ordered_search_result_items),
                ).format(n=len(ordered_search_result_items)),
                5000,
            )
            self.adv_search_model.sync({"search_results": ordered_search_result_items})

    def _get_adv_search_thread(
        self, overdrive_client, library_key: str, query: LibraryMediaSearchParams
    ):
        thread = QThread()
        worker = OverDriveLibraryMediaSearchWorker()
        worker.setup(overdrive_client, library_key, query)
        worker.moveToThread(thread)
        thread.library_key = library_key
        thread.worker = worker
        thread.started.connect(worker.run)

        def done(lib_key: str, results: Dict):
            thread.quit()
            self._process_search_results(lib_key, results.get("items", []))

        def errored_out(lib_key: str, err: Exception):
            thread.quit()
            self.logger.warning(
                "Error encountered during search (%s): %s", lib_key, err
            )
            self.gui.status_bar.show_message(
                _("Error encountered during search ({library}): {error}").format(
                    library=lib_key, error=str(err)
                ),
                5000,
            )
            self._process_search_results(lib_key, [])

        worker.finished.connect(lambda lib_key, results: done(lib_key, results))
        worker.errored.connect(lambda lib_key, err: errored_out(lib_key, err))

        return thread
