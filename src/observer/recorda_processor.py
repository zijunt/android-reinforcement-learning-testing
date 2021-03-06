"""The DataProcessor class."""
from utils import write_activity_json_to_files
import os

class DataProcessor:
    """Process the rawdata from Recorda."""

    def __init__(self, output_path):
        if not os.path.isdir(output_path):
            os.mkdir(output_path)
        self.output_path = output_path

    def groupByActivity(self, events):
        """Group the events by activity.

        if eventType is TYPE_WINDOW_STATE_CHANGED, the following event must be
        inside that activity.
        """
        currentActivity = 'unknownActivity'
        event_dict = {}
        for e in events:
            if e["eventType"] == 'TYPE_WINDOW_STATE_CHANGED':
                currentActivity = e["className"]

                if currentActivity not in event_dict:
                    event_dict[currentActivity] = []

            event_dict[currentActivity] += [e]

        return event_dict

    def check_scroll_type(self, event):
        """Check the scroll_type.

        if index-based -> list
        scroll-based -> scroll
        other -> invalid.
        """
        type = 'invalid'
        if event['eventType'] != 'TYPE_VIEW_SCROLLED':
            return type

        if event['scrollY'] != -1 and event['scrollX'] != -1:
            type = 'scroll'
        elif event['fromIndex'] != -1 and event['toIndex'] != -1:
            type = 'list'

        return type

    def get_scroll_key(self, type):
        """Return scroll key."""
        if type == 'scroll':
            return 'scrollY'
        elif type == 'list':
            return 'toIndex'
        else:
            return 'invalid'

    def get_direction(self, fromY, toY, lastDirection):
        """Get scroll direction."""
        di = lastDirection

        if lastDirection == 'none':
            if toY > fromY:
                di = 'swipe_up'
            elif toY < fromY:
                di = 'swipe_down'
        elif lastDirection == 'swipe_up':
            if toY < fromY:
                di = 'swipe_down'

        elif lastDirection == 'swipe_down':
            if toY > fromY:
                di = 'swipe_up'

        return di

    def squash_first_scroll_event(self, events, lastY=0):
        """Find consecutive scroll events."""
        direction = 'none'
        first_event = True
        scroll_event_list = []
        start, end, cur = [0, 0, 0]

        #  TODO: refactor this pyramid.
        for e in events:
            if e["eventType"] == 'TYPE_VIEW_SCROLLED' and self.check_scroll_type(e) != 'invalid':
                # List or scroll.
                key = self.get_scroll_key(self.check_scroll_type(e))
                thisY = e[key]
                if first_event:
                    scroll_event_list += [e]
                    start = cur
                    direction = self.get_direction(lastY, thisY, direction)
                    first_event = False

                elif direction == 'none':
                    direction = self.get_direction(lastY, thisY, direction)

                elif direction == 'swipe_up':
                    direction = self.get_direction(lastY, thisY, direction)
                    if direction == 'swipe_up':
                        lastY = thisY
                        scroll_event_list += [e]
                    elif direction == 'swipe_down':
                        end = cur - 1
                        break

                elif direction == 'swipe_down':
                    direction = self.get_direction(lastY, thisY, direction)
                    if direction == 'swipe_down':
                        lastY = thisY
                        scroll_event_list += [e]
                    elif direction == 'swipe_up':
                        end = cur - 1
                        break

            elif not first_event:
                end = cur-1
                break
            cur += 1
        return [start, end, scroll_event_list]

    def squash_all_scroll_events(self, events):
        """Squash the scroll events to a single event(non-optimized!)."""
        squashed = []
        remains = events
        curY = 0

        while len(remains) > 0:
            if remains[0]["eventType"] != 'TYPE_VIEW_SCROLLED':
                squashed += [remains[0]]
                remains = remains[1:len(remains)]
            else:
                firstScroll = self.squash_first_scroll_event(
                    remains, lastY=curY)
                if len(firstScroll[2]) != 0:
                    key = self.get_scroll_key(
                        self.check_scroll_type(firstScroll[2][0]))
                    firstIndex = firstScroll[0]
                    lastIndex = firstScroll[1]
                    squashed += remains[0:firstIndex]
                    squashed += [remains[lastIndex]]
                    curY = firstScroll[2][-1][key]
                    if lastIndex != len(remains)-1:
                        remains = remains[lastIndex+1:len(remains)]
                    else:
                        squashed += remains
                        break

        return squashed

    def remove_all_invalid_scroll_event(self, events):
        """Remove all invalid scroll event type."""
        return filter(lambda e: self.check_scroll_type(e) != 'invalid' or
                      e['eventType'] != 'TYPE_VIEW_SCROLLED', events)

    def process_all_events(self, events):
        """Process events.

        Squash all scroll event then group by activity then save to file.
        """
        squashed_events = self.squash_all_scroll_events(
            self.remove_all_invalid_scroll_event(events))
        grouped_events = self.groupByActivity(squashed_events)
        write_activity_json_to_files(grouped_events, path=self.output_path)


# sample json.
# {
# 		"className": "android.widget.ScrollView",
# 		"currentItemIndex": -1,
# 		"eventText": "[]",
# 		"eventTime": "42296811",
# 		"eventType": "TYPE_VIEW_SCROLLED",
# 		"fromIndex": -1,
# 		"idName": "com.octtoplus.proj.recorda:id/mainScroll",
# 		"isChecked": false,
# 		"isEnable": true,
# 		"isPassword": false,
# 		"itemCount": -1,
# 		"packageName": "com.octtoplus.proj.recorda",
# 		"scrollX": 0,
# 		"scrollY": 220,
# 		"toIndex": -1
# 	}
