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
        curr = profile_db.list_curr_accounts_balances(tracker.sender_id)
        formatted_curr = "\n" + "\n".join(
            [f"Card:{cur[0]}, currency: {cur[1]}, balance: {cur[2]}" for cur in curr])
        dispatcher.utter_message(
            response="utter_curr_accounts",
            formatted_accounts = formatted_curr,
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


class ActionShowCurrencies(Action):

    def name(self) -> Text:
        return "action_show_currencies"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        curr = profile_db.list_curr(tracker.sender_id)
        formatted_curr = "\n" + "\n".join(
            [f"{cur} - {curr[cur]}" for cur in curr.keys()]
        )
        dispatcher.utter_message(
            response="utter_currencies",
            formatted_accounts = formatted_curr,
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
        profile_db.creat_curr_acc(tracker.sender_id, tracker.get_slot('credit_card'), tracker.get_slot("currency"))

        dispatcher.utter_message(f"{tracker.get_slot('currency')} for {tracker.get_slot('credit_card')} is added")
        # return [SlotSet("currency", None),SlotSet("credit_card", None)]


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
        # slots = {
        #     "AA_CONTINUE_FORM": None,
        #     "zz_confirm_form": None,
        #     "currency": None,
        #     "account_type": None,
        #     "amount-of-money": None,
        #     "time": None,
        #     "time_formatted": None,
        #     "start_time": None,
        #     "end_time": None,
        #     "start_time_formatted": None,
        #     "end_time_formatted": None,
        #     "grain": None,
        #     "number": None,
        # }
        #
        # if tracker.get_slot("zz_confirm_form") == "yes":
        #     currency = tracker.get_slot("currency")
        #     profile_db.creat_curr_acc(
        #         tracker.sender_id, currency
        #     )
        #
        #     dispatcher.utter_message(response="utter_curr_acc_created", currency = currency)
        #
        #     slots["currency"] = currency
        # else:
        #     dispatcher.utter_message(response="utter_curr_acc_canceled")
        #
        # return [SlotSet(slot, value) for slot, value in slots.items()]

class ValidateCreateCurrencyAccount(CustomFormValidationAction):
    """Validates Slots of the curr_create_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_curr_create_form"




    async def validate_credit_card(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'credit_card' slot"""
        if value and value.lower() in profile_db.list_credit_cards(tracker.sender_id):
            credit_card_slot = {"credit_card": value.title()}
            return credit_card_slot
        dispatcher.utter_message(response="utter_no_creditcard")
        return {"credit_card": None}

    async def validate_currency(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'currency' slot"""
        curr = ['cny', 'gbp', 'eur', 'usd']
        list_of_cur = profile_db.list_curr_accounts_balances(tracker.sender_id)
        card_name = tracker.get_slot('credit_card')
        list_of_curr = [list_of_cur[i][1] for i in range(len(list_of_cur)) if list_of_cur[i][0].lower() == card_name.lower()]
        entity = get_entity_details(
            tracker, "currency"
        )
        amount_currency = parse_duckling_currency(entity).get('currency')
        if not amount_currency:
            return {"currency": None}
        if amount_currency.lower() not in curr:
            dispatcher.utter_message("I can't understand currency you entered")
            return {"currency": None}
        if amount_currency in list_of_curr:
            dispatcher.utter_message(response="utter_curr_exist")
            return {"currency": None}
        else:
            return SlotSet("currency", amount_currency)



        # try:
        #     entity = get_entity_details(
        #         tracker, "amount-of-money"
        #     ) or get_entity_details(tracker, "number")
        #     amount_currency = parse_duckling_currency(entity)
        #     if not amount_currency:
        #         raise TypeError
        #     if account_balance < float(amount_currency.get("amount-of-money")):
        #         dispatcher.utter_message(response="utter_insufficient_funds")
        #         return {"amount-of-money": None}
        #     return amount_currency
        # except (TypeError, AttributeError):
        #     pass

        # dispatcher.utter_message(response="utter_no_payment_amount")
        # return {"amount-of-money": None}



    # async def validate_zz_confirm_form(
    #     self,
    #     value: Text,
    #     dispatcher: CollectingDispatcher,
    #     tracker: Tracker,
    #     domain: Dict[Text, Any],
    # ) -> Dict[Text, Any]:
    #     """Validates value of 'zz_confirm_form' slot"""
    #     if value in ["yes", "no"]:
    #         return {"zz_confirm_form": value}
    #
    #     return {"zz_confirm_form": None}