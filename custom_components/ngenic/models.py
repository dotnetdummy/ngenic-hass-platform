from typing import List, TypedDict, Optional

# Based on usage in climate.py: tune["roomToControlUuid"], tune["rooms"], tune["name"]
# and ngenicpy.models.tune.Tune
class RoomTypedDict(TypedDict):
    uuid: str
    name: str
    nodeUuid: str # Or is it nodeUuid? Based on climate.py control_room["nodeUuid"]
    targetTemperature: float
    activeControl: bool
    # Add other fields if known or as they are discovered

class TuneTypedDict(TypedDict):
    uuid: str
    name: str
    roomToControlUuid: Optional[str]
    rooms: List[RoomTypedDict] # Assuming rooms is a list of Room-like dicts
    # Add other fields if known

# Based on usage in climate.py: control_node.uuid()
# and ngenicpy.models.node.Node
# This might represent the structure if a Node object were a dictionary
class NodeTypedDict(TypedDict):
    uuid: str
    # name: str # Often nodes have names
    # type: str # And types
    # other fields...

# Based on usage in climate.py: current["value"]
# and ngenicpy.models.measurement.Measurement
class MeasurementTypedDict(TypedDict):
    value: float
    # timestamp: str # Measurements usually have timestamps
    # unit: str # And units
