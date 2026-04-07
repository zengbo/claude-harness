package handlers

import (
    "internal/services"
    "cmd"
)

func HandleUser() {
    _ = cmd.Version
    services.GetUser(1)
}
