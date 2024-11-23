API_URL = "https://app.ngenic.se/api/v3"

API_PATH = {
  "tunes":                  "tunes/{tuneUuid}",
  "rooms":                  "tunes/{tuneUuid}/rooms/{roomUuid}",
  "nodes":                  "tunes/{tuneUuid}/gateway/nodes/{nodeUuid}",
  "node_status":            "tunes/{tuneUuid}/nodestatus",
  "measurements":           "tunes/{tuneUuid}/measurements/{nodeUuid}",
  "measurements_types":     "tunes/{tuneUuid}/measurements/{nodeUuid}/types",
  "measurements_latest":    "tunes/{tuneUuid}/measurements/{nodeUuid}/latest"
}
