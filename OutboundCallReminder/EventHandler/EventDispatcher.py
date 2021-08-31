from Logger import Logger
from threading import Lock
import threading
import json
from azure.core.messaging import CloudEvent
from azure.communication.callingserver._generated.models import CallConnectionStateChangedEvent, ToneReceivedEvent, \
    PlayAudioResultEvent, AddParticipantResultEvent
from azure.communication.callingserver._generated.models._azure_communication_calling_server_service_enums import *


class EventDispatcher:
    __instance = None
    notification_callbacks: dict = None
    subscription_lock = None

    def __init__(self):
        self.notification_callbacks = dict()
        self.subscription_lock = Lock()

    @staticmethod
    def get_instance():
        if EventDispatcher.__instance is None:
            EventDispatcher.__instance = EventDispatcher()

        return EventDispatcher.__instance

    def subscribe(self, event_type: str, event_key: str, notification_callback):
        self.subscription_lock.acquire
        event_id: str = self.build_event_key(event_type, event_key)
        self.notification_callbacks[event_id] = notification_callback
        self.subscription_lock.release

    def unsubscribe(self, event_type: str, event_key: str):
        self.subscription_lock.acquire
        event_id: str = self.build_event_key(event_type, event_key)
        del self.notification_callbacks[event_id]
        self.subscription_lock.release

    def build_event_key(self, event_type: str, event_key: str):
        return event_type + "-" + event_key

    def process_notification(self, request: str):
        call_event = self.extract_event(request)
        if call_event is not None:
            self.subscription_lock.acquire
            notification_callback = self.notification_callbacks.get(self.get_event_key(call_event))
            if (notification_callback != None):
                threading.Thread(target=notification_callback, args=(call_event,)).start()


    def get_event_key(self, call_event_base):
        if type(call_event_base) == CallConnectionStateChangedEvent:
            call_leg_id = call_event_base.call_connection_id
            key = self.build_event_key(CallingServerEventType.CALL_CONNECTION_STATE_CHANGED_EVENT, call_leg_id)
            return key
        elif type(call_event_base) == ToneReceivedEvent:
            call_leg_id = call_event_base.call_connection_id
            key = self.build_event_key(CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id)
            return key
        elif type(call_event_base) == PlayAudioResultEvent:
            operation_context = call_event_base.operation_context
            key = self.build_event_key(CallingServerEventType.PLAY_AUDIO_RESULT_EVENT, operation_context)
            return key
        elif type(call_event_base) == AddParticipantResultEvent:
            operation_context = call_event_base.operation_context
            key = self.build_event_key(CallingServerEventType.ADD_PARTICIPANT_RESULT_EVENT, operation_context)
            return key
        return None


    def extract_event(self, content: str):
        try:
            event = CloudEvent.from_dict(json.loads(content)[0])
            if event.type == CallingServerEventType.CALL_CONNECTION_STATE_CHANGED_EVENT:
                call_connection_state_changed_event = CallConnectionStateChangedEvent.deserialize(event.data)
                return call_connection_state_changed_event

            if event.type == CallingServerEventType.PLAY_AUDIO_RESULT_EVENT:
                play_audio_result_event = PlayAudioResultEvent.deserialize(event.data)
                return play_audio_result_event

            if event.type == CallingServerEventType.ADD_PARTICIPANT_RESULT_EVENT:
                add_participant_result_event = AddParticipantResultEvent.deserialize(event.data)
                return add_participant_result_event

            if event.type == CallingServerEventType.TONE_RECEIVED_EVENT:
                tone_received_event = ToneReceivedEvent.deserialize(event.data)
                return tone_received_event

        except Exception as ex:
            Logger.log_message(Logger.ERROR, "Failed to parse request content Exception: " + str(ex))

        return None
