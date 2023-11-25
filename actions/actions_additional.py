import os
from typing import Dict, Text, Any, List
import logging
from dateutil import parser
import sqlalchemy as sa

from rasa_sdk.interfaces import Action
from rasa_sdk.events import (
    SlotSet,
    EventType,
    ActionExecuted,
    SessionStarted,
    Restarted,
    FollowupAction,
    UserUtteranceReverted,
)
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.parsing import (
    parse_duckling_time_as_interval,
    parse_duckling_time,
    get_entity_details,
    parse_duckling_currency,
)

from actions.profile_db import create_database, ProfileDB

from actions.custom_forms import CustomFormValidationAction


logger = logging.getLogger(__name__)

# The profile database is created/connected to when the action server starts
# It is populated the first time `ActionSessionStart.run()` is called .

PROFILE_DB_NAME = os.environ.get("PROFILE_DB_NAME", "profile")
PROFILE_DB_URL = os.environ.get("PROFILE_DB_URL", f"sqlite:///{PROFILE_DB_NAME}.db")
ENGINE = sa.create_engine(PROFILE_DB_URL)
create_database(ENGINE, PROFILE_DB_NAME)

profile_db = ProfileDB(ENGINE)

NEXT_FORM_NAME = {
    "pay_cc": "cc_payment_form",
    "transfer_money": "transfer_money_form",
    "search_transactions": "transaction_search_form",
    "check_earnings": "transaction_search_form",
}

FORM_DESCRIPTION = {
    "cc_payment_form": "credit card payment",
    "transfer_money_form": "money transfer",
    "transaction_search_form": "transaction search",
}


class ActionShowAccounts(Action):
    """List of the credit card accounts"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_show_accounts"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        """Executes the custom action"""
        accounts = profile_db.list_credit_cards(tracker.sender_id)
        formatted_accounts = "\n" + "\n".join(
            [f"- {account.title()}" for account in accounts]
        )
        dispatcher.utter_message(
            response="utter_accounts",
            formatted_accounts = formatted_accounts,
        )

        events = []
        active_form_name = tracker.active_form.get("name")
        if active_form_name:
            # keep the tracker clean for the predictions with form switch stories
            events.append(UserUtteranceReverted())
            # trigger utter_ask_{form}_AA_CONTINUE_FORM, by making it the requested_slot
            events.append(SlotSet("AA_CONTINUE_FORM", None))
            # # avoid that bot goes in listen mode after UserUtteranceReverted
            events.append(FollowupAction(active_form_name))

        return events

class ActionShowCurrencyAccounts(Action):
    """List of the currency accounts"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_show_currency_accounts"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        """Executes the custom action"""
        accounts = profile_db.list_curr_accounts(tracker.sender_id)
        formatted_accounts = "\n" + "\n".join(
            [account for account in accounts]
        )
        dispatcher.utter_message(
            response="utter_curr_accounts",
            formatted_accounts = formatted_accounts,
        )

        events = []
        active_form_name = tracker.active_form.get("name")
        if active_form_name:
            # keep the tracker clean for the predictions with form switch stories
            events.append(UserUtteranceReverted())
            # trigger utter_ask_{form}_AA_CONTINUE_FORM, by making it the requested_slot
            events.append(SlotSet("AA_CONTINUE_FORM", None))
            # # avoid that bot goes in listen mode after UserUtteranceReverted
            events.append(FollowupAction(active_form_name))

        return events


class CreateCurrencyAccount(Action):
    """Create currency account"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_create_curr_acc"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""

        slots = {
            "AA_CONTINUE_FORM": None,
            "zz_confirm_form": None,
            "credit_card": None,
            "account_type": None,
            "amount-of-money": None,
            "time": None,
            "time_formatted": None,
            "start_time": None,
            "end_time": None,
            "start_time_formatted": None,
            "end_time_formatted": None,
            "grain": None,
            "number": None,
        }

        if tracker.get_slot("zz_confirm_form") == "yes":
            credit_card = tracker.get_slot("credit_card")
            amount_of_money = float(tracker.get_slot("amount-of-money"))
            amount_transferred = float(tracker.get_slot("amount_transferred"))
            profile_db.pay_off_credit_card(
                tracker.sender_id, credit_card, amount_of_money
            )

            dispatcher.utter_message(response="utter_cc_pay_scheduled")

            slots["amount_transferred"] = amount_transferred + amount_of_money
        else:
            dispatcher.utter_message(response="utter_cc_pay_cancelled")

        return [SlotSet(slot, value) for slot, value in slots.items()]